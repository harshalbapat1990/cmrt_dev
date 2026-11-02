import React, { useMemo, useState , useEffect } from "react";
import type { AdminAccessRequest } from "../types/access";

type Props = {
  items: AdminAccessRequest[];
  onOpen?: (r: AdminAccessRequest) => void;
  maxHeight?: number;
  sortByProp?: "dateRequested";
  sortDirProp?: "asc" | "desc";
};
type AccessType = "Edit" | "View";

const th =
  "px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-text-base bg-[#F7F7F7]";
const td =
  "px-4 py-3 text-sm text-slate-800 align-top border-t border-r border-slate-100";

const AccessTable: React.FC<Props> = ({
  items,
  onOpen,
  sortByProp,
  sortDirProp,
  maxHeight = 560,
}) => {
  //Sorting date by default and Z-A 
  const [sortBy, setSortBy] = useState<"requester" | "projectName" | "dateRequested">(
    sortByProp ?? "dateRequested"
  );
  const [sortDir, setSortDir] = useState<"asc" | "desc">(sortDirProp ?? "desc");

  
  useEffect(() => {
    if (sortByProp) setSortBy(sortByProp);
  }, [sortByProp]);
  useEffect(() => {
    if (sortDirProp) setSortDir(sortDirProp);
  }, [sortDirProp]);

  /** ---- Sorting helpers ---- */
  function parseISO(dateStr: string): number {
    // Accepts ISO (YYYY-MM-DD) or already-formatted strings.
    // If not ISO, treat as Date.parse fallback (NaN-safe)
    const iso = /^\d{4}-\d{2}-\d{2}$/.test(dateStr)
      ? new Date(dateStr + "T00:00:00")
      : new Date(dateStr);
    return iso.getTime();
  }
  function normalizeProjectCategory(cat?: string) {
    if (!cat) return "";
    const labels: Record<string, string> = {
      small: "Small",
      large: "Large",
      recurring: "Recurring",
    };
    return labels[cat.toLowerCase()] ?? cat;
  }
  function compare(a: AdminAccessRequest, b: AdminAccessRequest): number {
    let primary = 0;

    
    const at = parseISO(a.dateRequested as unknown as string);
    const bt = parseISO(b.dateRequested as unknown as string);
    primary = at === bt ? 0 : at < bt ? -1 : 1;
    

    if (primary === 0) {
      const at = parseISO(a.dateRequested as unknown as string);
      const bt = parseISO(b.dateRequested as unknown as string);
      if (at !== bt) primary = at < bt ? -1 : 1;
    }
    return sortDir === "asc" ? primary : -primary;
  }

  const sortedItems = useMemo(() => {
    const copy = [...items];
    copy.sort(compare);
    return copy;
  }, [items, sortBy, sortDir]);

  const groups = useMemo(() => {
    return sortedItems.map((req) => {
      const accessLabel : AccessType = req.requestedRole === "PROJECT_EDITOR" ? "Edit" : "View";
      const stages =
        req.stages && req.stages.length > 0
          ? req.stages
          : [{ name: "N/A", access: accessLabel }];
      return { req, stages };
    });
  }, [sortedItems]);

  /** ---- Header click handlers ---- */
  const toggleRequesterSort = () => {
    if (sortBy === "dateRequested") {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy("dateRequested");
      setSortDir("asc"); //latest records first 
    }
  };


  return (
    <section className=" rounded-[var(--radius-3)] border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-6 py-5">
        <h3 className="text-2xl font-light text-slate-900">
          Pending requests ({items.length})
        </h3>
      </div>

      <div className="max-h-[220px] overflow-y-auto scroll-styled no-scroll-buttons" style={{ maxHeight }}>
        <table className="min-w-full border-separate" style={{ borderSpacing: 0 }}>
          <thead className="bg-[#F7F7F7]">
            <tr>
              <th className={th} style={{ position: "sticky", top: 0 }}>
                Requested by
              </th>

              <th className={th} style={{ position: "sticky", top: 0 }}>
                Project name
              </th>

              <th className={th} style={{ position: "sticky", top: 0 }}>
                Project category
              </th>
              <th className={th} style={{ position: "sticky", top: 0 }}>
                Project stage
              </th>
              <th className={th} style={{ position: "sticky", top: 0 }}>
                Access
              </th>
               <th className={th} style={{ position: "sticky", top: 0 }}>
                <div className="flex items-center gap-1">
                  <span>Date requested</span>
                  <button
                    type="button"
                    onClick={toggleRequesterSort}
                    className="inline-flex items-center rounded p-1 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-300 cursor-pointer"
                    aria-label="Sort by date requested"
                    title="Sort by date requested"
                  >
                    <span
                      className="material-symbols-rounded text-gray-500"
                      style={{ fontSize: 18 }}
                    >
                      {sortBy === "dateRequested" && (
                          sortDir === "asc"
                          ? "arrow_drop_up"
                          : "arrow_drop_down"
                        )}

                    </span>
                  </button>
                </div>
              </th>
              <th className={th} style={{ position: "sticky", top: 0 }}>
                Action
              </th>
            </tr>
          </thead>

          <tbody>
            {groups.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-sm text-slate-500">
                  No pending requests.
                </td>
              </tr>
            ) : (
              groups.map(({ req, stages }) => {
                const rowSpan = Math.max(stages.length, 1);
                const isEven = sortedItems.findIndex((r: AdminAccessRequest) => r.id === req.id) % 2 === 0; // Determine even/odd based on original index
             
                return (
                  <React.Fragment key={req.id}>
                    {stages.map((s, idx) => (
                      <tr key={`${req.id}-${idx}`} className={isEven ? undefined: "bg-[#FCFCFC]" }>
                        {/* Row-spanned cells rendered only for the first stage row */}
                        {idx === 0 && (
                          <td className={td} rowSpan={rowSpan}>
                            <div>{req.requester}</div>
                          </td>
                        )}
                        {idx === 0 && (
                          <td className={td} rowSpan={rowSpan}>
                            {req.projectName}
                          </td>
                        )}
                       {idx === 0 && (
                        <td className={td} rowSpan={rowSpan}>
                          {normalizeProjectCategory(req.projectCategory)}
                        </td>
                      )}

                        {/* Stage + Access vary per row */}
                        <td className={td}>{s.name}</td>
                        <td className={td}>{s.access}</td>

                        {idx === 0 && (
                          <td className={td} rowSpan={rowSpan}>
                            {formatDate(req.dateRequested as unknown as string)}
                          </td>
                        )}
                        {idx === 0 && (
                          <td className={td} rowSpan={rowSpan}>
                            <button
                              type="button"
                              onClick={() => onOpen?.(req)}
                              className="text-sm text-primary font-medium cursor-pointer"
                            >
                              Review request
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default AccessTable;

/* ---------------- Helpers ---------------- */

function formatDate(input: string) {
  // Accepts ISO (YYYY-MM-DD) or date-time strings
  const match = input.match(/^\d{4}-\d{2}-\d{2}/);
  if (!match) return input;
  const d = new Date(match[0] + "T00:00:00");
  const day = d.getDate();
  const month = d.toLocaleString("en-GB", { month: "long" });
  const year = d.getFullYear();

  return `${day} ${month} ${year}`;
}
