# Stoichiometric Graph Builder with Live Network Visualization (fixed)
# FastHTML + DuckDB + Plotly + NetworkX
# - Uses NotStr to embed HTML
# - Correct Plotly layout usage
# - Dropdowns (Selects) restored and refreshed after inserts
from collections import deque
from fasthtml.common import *
from monsterui.all import *
import duckdb, uuid, networkx as nx
import plotly.graph_objects as go
from plotly.offline import plot
from fh_plotly import plotly2fasthtml, plotly_headers
import networkx as nx
import base64, json
import adlfs
import os


# ==== AZURE BLOB ACCESS =======

AZURE_SAS_TOKEN = os.getenv("AZURE_SAS_TOKEN")
AZURE_STORAGE_ACCOUNT_NAME  = "saaustroadscmrt"
AZURE_CONTAINER_NAME = "userauth"


BLOB_PATH = f"abfs://{AZURE_CONTAINER_NAME}/users/*.json"
fs = adlfs.AzureBlobFileSystem(
    account_name=AZURE_STORAGE_ACCOUNT_NAME,
    account_key = AZURE_SAS_TOKEN
)

# ========== DB SETUP ==========
conn = duckdb.connect(":memory:")

conn.register_filesystem(fs)


# ==== Optional Postgres Access ===
# We assume that if this env is given that there is a postgres to use
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
if POSTGRES_HOST is not None:
    # print("Using postgres as database")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    conn.execute("INSTALL postgres;")
    conn.execute(f"""
    CREATE SECRET (
        TYPE postgres,
        HOST '{POSTGRES_HOST}',
        PORT 5432,
        DATABASE postgres,
        USER '{POSTGRES_USER}',
        PASSWORD '{POSTGRES_PASSWORD}'
        );
    """)
    conn.execute("ATTACH '' AS postgres_db (TYPE postgres);")
    db_str = "postgres_db."
else:
    # print("Using local duckdb as database")
    db_str = ""

conn.execute(f"""
    CREATE TABLE IF NOT EXISTS {db_str}materials (
        id VARCHAR PRIMARY KEY,
        name VARCHAR NOT NULL,
        description VARCHAR,
        ts TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS {db_str}measures (
        id VARCHAR PRIMARY KEY,
        name VARCHAR NOT NULL,
        description VARCHAR,
        ts TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS {db_str}nodes (
        id VARCHAR PRIMARY KEY,
        material_id VARCHAR,
        measure_id  VARCHAR,
        ts TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS {db_str}links (
        id VARCHAR PRIMARY KEY,
        numerator_node_id   VARCHAR,
        denominator_node_id VARCHAR,
        value DOUBLE NOT NULL,
        ts TIMESTAMP DEFAULT NOW()
    );
""")

# Helper read views
conn.execute(f"""
    CREATE OR REPLACE VIEW v_nodes AS
    SELECT
        n.id,
        m.name  AS material,
        ms.name AS measure,
        n.ts
    FROM {db_str}nodes n
    JOIN {db_str}materials m ON m.id = n.material_id
    JOIN {db_str}measures  ms ON ms.id = n.measure_id;

    CREATE OR REPLACE VIEW v_links_all AS
    SELECT
        l.id,
        vn_num.measure || ' of ' || vn_num.material AS numerator_node,
        vn_den.measure || ' of ' || vn_den.material AS denominator_node,
        l.value,
        l.ts,
        l.numerator_node_id,
        l.denominator_node_id
    FROM {db_str}links l
    JOIN v_nodes vn_num ON vn_num.id = l.numerator_node_id
    JOIN v_nodes vn_den ON vn_den.id = l.denominator_node_id;

    -- Latest value per (numerator_node_id, denominator_node_id)
    CREATE OR REPLACE VIEW v_links_latest AS
    WITH ranked AS (
        SELECT
            l.*,
            ROW_NUMBER() OVER (
                PARTITION BY numerator_node_id, denominator_node_id
                ORDER BY ts DESC, id DESC
            ) AS rnk
        FROM {db_str}links l
    )
    SELECT
        r.id,
        vn_num.measure || ' of ' || vn_num.material AS numerator_node,
        vn_den.measure || ' of ' || vn_den.material AS denominator_node,
        r.value,
        r.ts,
        r.numerator_node_id,
        r.denominator_node_id
    FROM ranked r
    JOIN v_nodes vn_num ON vn_num.id = r.numerator_node_id
    JOIN v_nodes vn_den ON vn_den.id = r.denominator_node_id
    WHERE r.rnk = 1;
""")

# ========== FASTHTML APP + WS ==========
app, rt = fast_app(hdrs=(plotly_headers,Theme.gray.headers()), exts= "ws")
users = {}  # wsid -> send callable

# ========== HELPERS ==========
def check_user_auth(userid, conn):
    # print("checking user auth")
    user_check_query = f"""
    SELECT id, valid_until
    FROM read_json_auto('{BLOB_PATH}')
    WHERE id == '{userid}'
    """
    return conn.cursor().execute(user_check_query).df()
def _df(query: str):
    res = conn.cursor().execute(query)
    headers = [c[0] for c in res.description]
    body = res.df().to_dict('records')
    return headers, body

def _render_table(div_id: str, query: str):
    headers, body = _df(query)
    return Div(TableFromDicts(headers, body), id=div_id)

async def _broadcast(div_id: str, query: str):
    headers, body = _df(query)
    table_div = Div(TableFromDicts(headers, body), id=div_id)
    for send in users.values():
        await send(table_div)
        # When links change, refresh graph + link history as well
        if div_id in ("links_table", "links_history_table"):
            await send(Div(render_graph_html(), id="graph_div"))

def _material_options():
    rows = conn.cursor().execute(f"SELECT id, name FROM {db_str}materials ORDER BY name").fetchall()
    opts = [Option("— select material —", value="", selected=True, disabled=True)]
    opts += [Option(r[1], value=r[0]) for r in rows]
    return opts

def _measure_options():
    rows = conn.cursor().execute(f"SELECT id, name FROM {db_str}measures ORDER BY name").fetchall()
    opts = [Option("— select measure —", value="", selected=True, disabled=True)]
    opts += [Option(r[1], value=r[0]) for r in rows]
    return opts

def _node_options():
    rows = conn.cursor().execute(f"""
        SELECT n.id, ms.name || ' of ' || m.name AS label
        FROM {db_str}nodes n
        JOIN {db_str}materials m ON m.id = n.material_id
        JOIN {db_str}measures  ms ON ms.id = n.measure_id
        ORDER BY ms.name, m.name
    """).fetchall()
    opts = [Option("— select node —", value="", selected=True, disabled=True)]
    opts += [Option(r[1], value=r[0]) for r in rows]
    return opts

def _link_options():
    rows = conn.cursor().execute("SELECT numerator_node, denominator_node, value FROM v_links_latest").fetchall()
    opts = [Option("— select link —", value="", selected=True, disabled=True)]
    opts += [Option(r[1], value=r[0]) for r in rows]
    return opts


def _build_graph():
    """
    Build a NetworkX graph from database relationships
    Returns the graph object with bidirectional edges and inverted weights for reverse direction
    """
    try:
        # Create directed graph
        G = nx.DiGraph()

        # Get all relationships from the database
        rows = conn.cursor().execute("SELECT numerator_node_id, denominator_node_id, value FROM v_links_latest").fetchall()

        if not rows:
            return G

        # Add edges to the graph with weights (conversion factors)
        for source, target, weight in rows:
            if source != target:  # Skip self-loops
                # Add forward edge
                G.add_edge(source, target, weight=weight)

                # Add reverse edge with inverted weight for unit conversion
                if weight != 0:  # Avoid division by zero
                    reverse_weight = 1.0 / weight
                    G.add_edge(target, source, weight=reverse_weight)

        return G

    except Exception as e:
        # print(f"Error building graph: {e}")
        return nx.DiGraph()


def _find_path_v2(start_node_id, end_node_id):
    """
    Find all simple paths from start_node_id → end_node_id in the current NetworkX graph.
    For each path, multiply edge weights along the route.
    Return a list of (path_nodes, path_factor) and the total (sum of all path factors).
    """

    G = _build_graph()  # your existing function that returns nx.DiGraph()

    if not G.has_node(start_node_id) or not G.has_node(end_node_id):
        return [], 0.0

    all_paths = list(nx.all_simple_paths(G, start_node_id, end_node_id))
    if not all_paths:
        return [], 0.0

    path_results = []
    total_factor = 0.0

    for path in all_paths:
        # multiply weights along path
        factors = []
        for u, v in zip(path[:-1], path[1:]):
            weight = G[u][v].get("weight", 1.0)
            factors.append(weight)

        path_factor = math.prod(factors)
        path_results.append((path, path_factor))
        total_factor += path_factor

    return path_results, total_factor

def _node_name(node_id: str):
    return conn.cursor().execute(f"""
        SELECT ms.name || ' of ' || m.name AS label
        FROM {db_str}nodes n
        JOIN {db_str}materials m ON m.id = n.material_id
        JOIN {db_str}measures  ms ON ms.id = n.measure_id
        Where n.id = '{node_id}'""").fetchone()[0]

# ========== GRAPH VISUALIZATION ==========
def render_graph_html():
    rows = conn.cursor().execute("SELECT numerator_node, denominator_node, value FROM v_links_latest").fetchall()
    if not rows:
        return "<div style='padding:8px;color:#94a3b8;'>No links defined yet.</div>"

    # Build graph: denominator -> numerator (so multiplying follows edge direction)
    G = nx.DiGraph()
    for num, den, val in rows:
        G.add_edge(den, num, weight=val)

    # Layout
    pos = nx.random_layout(G)

    # Edges
    edge_x, edge_y = [], []
    edge_text = []
    for u, v, d in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        edge_text.append(f"{u} → {v}<br>value = {d['weight']}")

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=1),
        hoverinfo="text",
        text=edge_text
    )

    # Nodes
    node_x, node_y, node_text = [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y); node_text.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        hoverinfo='text',
        marker=dict(size=16, line=dict(width=2))
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title_text="Stoichiometric Graph Network",
        title_x=0.5,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=10, l=10, r=10, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )

    # Return embeddable div string, include plotlyjs via CDN
    return plotly2fasthtml(fig)

# ---------- UI fragments ----------
def MaterialForm():
    return Form(
        Grid(
            Input(id="material_name", name="material_name", placeholder="Material name (e.g., Asphalt)", required=True),
            Textarea(id="material_desc", name="material_desc", placeholder="Description (optional)", rows=2),
            cols=2
        ),
        Button("Add Material"),
        hx_post="/insert_material", hx_target="#material_notice", hx_swap="innerHTML"
    )

def MeasureForm():
    return Form(
        Grid(
            Input(id="measure_name", name="measure_name", placeholder="Measure (e.g., cubic metres)", required=True),
            Textarea(id="measure_desc", name="measure_desc", placeholder="Description (optional)", rows=2),
            cols=2
        ),
        Button("Add Measure"),
        hx_post="/insert_measure", hx_target="#measure_notice", hx_swap="innerHTML"
    )

def NodeForm():
    return Form(
        Grid(
            Select(*_measure_options(), id="measure_id", name="measure_id", icon=True, required=True, placeholder="Select measure"),
            Select(*_material_options(), id="material_id", name="material_id", icon=True, required=True, placeholder="Select material"),
            cols=2
        ),
        Button("Add Node"),
        hx_post="/insert_node", hx_target="#node_notice", hx_swap="innerHTML"
    )

def LinkForm():
    return Form(
        Grid(
            Div('1', style="width: 20px; padding: 0; margin: 0;"),
            Select(*_node_options(), id="numerator_node_id", name="numerator_node_id", icon=True, required=True, placeholder="Numerator node"),
            Div('is', style="width: 20px; padding: 0; margin: 0;"),
            Input(id="value", name="value", type="number", step="any", placeholder="Numeric value", required=True, style="min-width: 80px;"),
            Select(*_node_options(), id="denominator_node_id", name="denominator_node_id", icon=True, required=True, placeholder="Denominator node"),
            cols=5,
            style="grid-template-columns: min-content auto min-content auto min-content;"
        ),
        Button("Add / Update Link (append-only)"),
        hx_post="/insert_link", hx_target="#link_notice", hx_swap="innerHTML"
    )

def ConversionForm():
    """
    The goal of conversion form is to make the conversion from one node to another given the starting value.
    This requires the following:
    1. the starting node
    2. the ending node
    3. the value at the starting node
    """
    return Form(
        H3("Convert"),
        Input(id="value", name="value", type="number", step="any", placeholder="Amount", required=True),
        Select(*_node_options(), id="start_node_id", name="start_node_id", icon=True, required=True, placeholder="From"),
        Select(*_node_options(), id="end_node_id", name="end_node_id", icon=True, required=True, placeholder="To"),
        Button("Find Path", type="submit"),
        hx_post="/convert",
        hx_swap="innerHTML",
        hx_target="#conversion"
    )

def MultiConversionForm():
    """
    Form for adding multiple conversions to a table with automatic summation.
    Allows entering multiple conversion rows and displays results in a table.
    """
    return Div(
        H3("Multiple Conversions"),
        # Output selector
        Form(
            Grid(
                Input(id="value", name="amount", type="number", step="any", placeholder="Amount", required=True, style="width: 100px;"),
                Select(*_node_options(), id="end_node_id", name="end_node_id", icon=True, required=True,
                       placeholder="From node", style="min-width: 150px;"),
                Select(*_node_options(), id="start_node_id", name="start_node_id", icon=True, required=True, placeholder="To node", style="min-width: 150px;"),
                rows=3
            ),
            Button("Add Conversion Row", type="submit", style="margin-top: 10px;"),
            hx_post="/add_conversion_row",
            hx_target="#conversion_table_body",
            hx_swap="beforeend"
        ),
        # Table for conversions
        Table(
            Thead(
                Tr(
                    Th("Amount"),
                    Th("From Node"),
                    Th("Result"),
                    Th("End Node")
                )
            ),
            Tbody(
                id="conversion_table_body"
            ),
            style="width: 100%; margin-top: 15px;"
        ),
        # Total row
        Div(
            "Total: ",
            Span(id="total_amount", style="font-weight: bold;"),
            style="margin-top: 10px; text-align: right;"
        ),
        Script("""
                    document.addEventListener('htmx:afterRequest', function(evt) {
                        if (evt.detail.target.id === 'conversion_table_body') {
                            updateTotal();
                        }
                    });

                    function updateTotal() {
                        const rows = document.querySelectorAll('#conversion_table_body tr');
                        let total = 0;

                        rows.forEach(row => {
                            const resultCell = row.cells[2]; // Third cell contains the result
                            if (resultCell) {
                                const resultValue = parseFloat(resultCell.textContent);
                                if (!isNaN(resultValue)) {
                                    total += resultValue;
                                }
                            }
                        });

                        document.getElementById('total_amount').textContent = total.toFixed(2);
                    }
                """)
    )
# ========== AUTH ===========
def extract_username_from_github(req):
    raw = req.headers.get("x-ms-client-principal")
    if not raw:
        return None

    data = json.loads(base64.b64decode(raw))

    for claim in data["claims"]:
        if claim["typ"] == "urn:github:login":
            return claim["val"]

    return None

# ========== ROUTES ==========
@rt("/debug/headers")
async def debug_headers(req):
    # Convert headers to a normal dict so they’re easy to read
    hdrs = {k: v for k, v in req.headers.items()}
    return hdrs

@rt("/")
async def home(req):
    user = extract_username_from_github(req)
    valid_users = check_user_auth(user, conn)
    if valid_users.shape[0] < 1:
        return Titled(
            P(f"Hey {user}, get out of here")
        )
    return Titled(
        "Stoichiometric Graph Builder with Visualization",
        P(f"Hello, {user}!"),
        Div(
            Grid(
                Card(
                    H3("1) Materials"),
                    MaterialForm(),
                    Div(id="material_notice"),
                    Div(id="materials_table"),
                    cls="bg-slate-900 shadow-lg shadow-cyan-500/50 rounded-md"
                ),
                Card(
                    H3("2) Measures"),
                    MeasureForm(),
                    Div(id="measure_notice"),
                    Div(id="measures_table"),
                    cls="bg-slate-900 shadow-lg shadow-cyan-500/50 rounded-md"
                ),
                cols=2
            ),
            Div(cls="divider"),
            Grid(
                Card(
                    H3("3) Nodes"),
                    Div(NodeForm(), id="node_form_area"),
                    Div(id="node_notice"),
                    Div(id="nodes_table"),
                    cls="bg-slate-900 shadow-lg shadow-cyan-500/50 rounded-md"
                ),
                Card(
                    H3("4) Links"),
                    Div(LinkForm(), id="link_form_area"),
                    Div(id="link_notice"),
                    Div(H4("Current Links (latest per pair)")),
                    Div(id="links_table"),
                    Details(
                        Summary("History (all entries)"),
                        Div(id="links_history_table")
                    ),
                    cls="bg-slate-900 shadow-lg shadow-cyan-500/50 rounded-md"
                ),
                Card(
                    H3("5) Conversions"),
                    Div(MultiConversionForm(), id="conversion_form_area"),
                    Div(id="conversion_notice"),
                    Div(id="conversion"),
                    cls="bg-slate-900 shadow-lg shadow-cyan-500/50 rounded-md"
                ),
                cols=3
            ),
            Div(cls="divider"),
            Card(
                H3("5) Graph Visualization"),
                Div(render_graph_html(), id="graph_div"),
                cls="bg-slate-900 shadow-lg shadow-cyan-500/50 rounded-md"
            ),
            hx_ext='ws',
            ws_connect='/ws'
        )
    )

# ========== INSERT HANDLERS ==========
@rt("/insert_material")
async def insert_material(material_name: str, material_desc: str = ""):
    conn.cursor().execute(f"INSERT INTO {db_str}materials VALUES (?, ?, ?, NOW())", (str(uuid.uuid4()), material_name.strip(), material_desc.strip() or None))
    await _broadcast("materials_table", f"SELECT id, name, description, ts FROM {db_str}materials ORDER BY ts DESC")
    # refresh dependent forms
    node_form, link_form = Div(NodeForm(), id="node_form_area"), Div(LinkForm(), id="link_form_area")
    for send in users.values():
        await send(node_form)
        await send(link_form)
    return Alert("✅ Material added.")

@rt("/insert_measure")
async def insert_measure(measure_name: str, measure_desc: str = ""):
    conn.cursor().execute(f"INSERT INTO {db_str}measures VALUES (?, ?, ?, NOW())", (str(uuid.uuid4()), measure_name.strip(), measure_desc.strip() or None))
    await _broadcast("measures_table",f"SELECT id, name, description, ts FROM {db_str}measures ORDER BY ts DESC")
    # refresh dependent forms
    node_form, link_form = Div(NodeForm(), id="node_form_area"), Div(LinkForm(), id="link_form_area")
    for send in users.values():
        await send(node_form)
        await send(link_form)
    return Alert("✅ Measure added.")

@rt("/insert_node")
async def insert_node(material_id: str, measure_id: str):
    conn.cursor().execute(f"INSERT INTO {db_str}nodes VALUES (?, ?, ?, NOW())", (str(uuid.uuid4()), material_id, measure_id))
    await _broadcast("nodes_table", "SELECT id, material, measure, ts FROM v_nodes ORDER BY ts DESC")
    # refresh link form
    link_form, conversion_form = Div(LinkForm(), id="link_form_area"), Div(MultiConversionForm(), id="conversion_form_area")
    for send in users.values():
        await send(link_form)
        await send(conversion_form)
    return Alert("✅ Node added.")

@rt("/insert_link")
async def insert_link(numerator_node_id: str, denominator_node_id: str, value: float):
    conn.cursor().execute(f"INSERT INTO {db_str}links VALUES (?, ?, ?, ?, NOW())", (str(uuid.uuid4()), numerator_node_id, denominator_node_id, float(value)))
    # update current + history + graph
    await _broadcast("links_table", "SELECT id, numerator_node, denominator_node, value, ts FROM v_links_latest ORDER BY ts DESC")
    await _broadcast("links_history_table", "SELECT id, numerator_node, denominator_node, value, ts FROM v_links_all ORDER BY ts DESC")
    return Alert("✅ Link appended. Graph updated.")


@rt("/convert", methods=["POST"])
async def convert_post(req):
    """
    Handle form submission and find path between nodes
    """
    form_data = await req.form()

    try:
        value = float(form_data.get('value', 0))
        start_node_id = form_data.get('start_node_id', 0)
        end_node_id = form_data.get('end_node_id', 0)

        if not start_node_id or not end_node_id:
            return Alert("Please select both start and end nodes")

        # Find the path
        path, factor = _find_path_v2(start_node_id, end_node_id)

        if not path:
            return Alert("No path found between selected nodes")

        return Alert(value*factor)

        # return Div(
        #     H3("Conversion Path Found"),
        #     P(f"Converting {value} units from {start_node_id} to {end_node_id}"),
        #     P(f"Total nodes in path: {path}")
        # )

    except Exception as e:
        return Div(f"Error processing conversion: {str(e)}")


@rt("/add_conversion_row", methods=["POST"])
async def add_conversion_row(req):
    """
    Handle adding a new conversion row to the table
    """
    form_data = await req.form()

    try:
        value = float(form_data.get('amount', 0))
        start_node_id = form_data.get('start_node_id', 0)
        end_node_id = form_data.get('end_node_id', 0)

        if not start_node_id or not end_node_id:
            return Alert("Please select both start and end nodes")

        # Find the path
        path, factor = _find_path_v2(start_node_id, end_node_id)

        if not path:
            return Alert("No path found between selected nodes")

        row = Tr(
            Td(value),
            Td(_node_name(start_node_id)),
            Td(value*factor),  # Placeholder for result - would be calculated in real app
            Td(_node_name(end_node_id))
            # Td(
            #     Button("Delete", onclick=f"deleteRow(this)",
            #            style="background-color: red; color: white; border: none; padding: 5px 10px; margin-right: 5px;"),
            # )
        )

        return row

    except Exception as e:
        return Div(f"Error adding conversion row: {str(e)}")

@rt("/update_hidden_end_node", methods=["POST"])
async def update_hidden_end_node(req):
    form_data = await req.form()
    selected_value = form_data.get("end_node_id")
    return Input(type="hidden", id="hidden_end_node", name="end_node_id", value=selected_value)

# ========== WS ==========
def on_disconn(ws):
    users.pop(str(id(ws)), None)

async def on_conn(send, ws):
    users[str(id(ws))] = send
    await send(Div("Welcome! Add data to see the network update live.", id="welcome"))
    await send(_render_table("materials_table", f"SELECT id, name, description, ts FROM {db_str}materials ORDER BY ts DESC"))
    await send(_render_table("measures_table",  f"SELECT id, name, description, ts FROM {db_str}measures ORDER BY ts DESC"))
    await send(_render_table("nodes_table",     "SELECT id, material, measure, ts FROM v_nodes ORDER BY ts DESC"))
    await send(_render_table("links_table",     "SELECT id, numerator_node, denominator_node, value, ts FROM v_links_latest ORDER BY ts DESC"))
    await send(_render_table("links_history_table", "SELECT id, numerator_node, denominator_node, value, ts FROM v_links_all ORDER BY ts DESC"))
    await send(Div(render_graph_html(), id="graph_div"))

@app.ws('/ws', conn=on_conn, disconn=on_disconn)
async def ws(send, ws):
    pass

# ========== RUN ==========
serve(host='0.0.0.0')
