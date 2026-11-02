import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConcreteRegisterService } from "@/services/ConcreteRegister.service";
import type { ConcreteMixOut } from "@/services/ConcreteRegister.service";
import { useConcreteRegisterData } from "./useConcreteRegisterData";

vi.mock("@/services/ConcreteRegister.service", () => ({
  ConcreteRegisterService: { listMixes: vi.fn() },
}));

const row: ConcreteMixOut = {
  id: "mix", project_id: "project", method: "simplified", mix_type: null,
  strength_mpa: 25, scm_pct: null, mix_id_label: null, gwp_a1a3: null,
  volume_m3: 3, emissions_tco2e: 1.2, notes: null, sort_order: 0,
  materials: [], created_on: null, updated_on: null,
};

describe("useConcreteRegisterData", () => {
  beforeEach(() => vi.mocked(ConcreteRegisterService.listMixes).mockReset());

  it("loads the selected project and exposes mapped rows", async () => {
    vi.mocked(ConcreteRegisterService.listMixes).mockResolvedValue([row]);
    const { result } = renderHook(() => useConcreteRegisterData("project"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(ConcreteRegisterService.listMixes).toHaveBeenCalledWith("project");
    expect(result.current.simplifiedRows[0]).toMatchObject({ id: "mix", strengthMpa: "25", volumeM3: 3 });
  });

  it("does not apply a stale response after the project changes", async () => {
    let resolveFirst!: (mixes: ConcreteMixOut[]) => void;
    vi.mocked(ConcreteRegisterService.listMixes)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }))
      .mockResolvedValueOnce([{ ...row, id: "new-project-mix" }]);
    const { result, rerender } = renderHook(({ projectId }) => useConcreteRegisterData(projectId), {
      initialProps: { projectId: "first" },
    });

    rerender({ projectId: "second" });
    await waitFor(() => expect(result.current.simplifiedRows[0]?.id).toBe("new-project-mix"));
    await act(async () => { resolveFirst([{ ...row, id: "stale-mix" }]); });
    expect(result.current.simplifiedRows[0]?.id).toBe("new-project-mix");
  });
});
