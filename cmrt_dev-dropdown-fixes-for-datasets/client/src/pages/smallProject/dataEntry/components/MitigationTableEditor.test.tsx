import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyMitigationTables } from "./MitigationTableEditor";
import type { MitigationTablesCollector } from "../Mitigations";

describe("EmptyMitigationTables", () => {
  it("collects the empty table rows for its lifecycle and submission stage", () => {
    const collectorRef = { current: null } as React.MutableRefObject<MitigationTablesCollector | null>;
    render(
      <EmptyMitigationTables
        submissionStage="Design"
        lifecyclePhase="construction"
        projectId="project"
        scopeKey="scenario-construction"
        collectorRef={collectorRef}
        hydrateTables={null}
        readOnly
        projectMitigationId="scenario"
        mitigationMode="reduction"
        substitutionLeg={null}
        mitigationStageInstanceId={null}
        mitigationProjectOptionId={null}
        projectTypeName={null}
        opsStartYear={null}
      />,
    );

    expect(collectorRef.current?.collect()).toEqual({
      component: [],
      bcDetailedLevel: [],
      electricity: [],
      concreteRegSimplified: [],
    });
  });

  it("hydrates provided rows into the collected snapshot", async () => {
    const collectorRef = { current: null } as React.MutableRefObject<MitigationTablesCollector | null>;
    render(
      <EmptyMitigationTables
        submissionStage="Design"
        lifecyclePhase="construction"
        projectId="project"
        scopeKey="scenario-construction"
        collectorRef={collectorRef}
        hydrateTables={{ component: [{ id: "row-1", quantity: 4 }] }}
        readOnly
        projectMitigationId="scenario"
        mitigationMode="reduction"
        substitutionLeg={null}
        mitigationStageInstanceId={null}
        mitigationProjectOptionId={null}
        projectTypeName={null}
        opsStartYear={null}
      />,
    );

    await waitFor(() => expect(collectorRef.current?.collect().component).toEqual([
      { id: "row-1", quantity: 4 },
    ]));
  });
});
