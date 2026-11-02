import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConcreteRegisterService } from "@/services/ConcreteRegister.service";
import type { ConcreteMixOut } from "@/services/ConcreteRegister.service";
import { useConcreteRegisterActions } from "./useConcreteRegisterActions";
import { useConcreteRegisterData } from "./useConcreteRegisterData";

vi.mock("@/services/ConcreteRegister.service", () => ({
  ConcreteRegisterService: {
    listMixes: vi.fn(),
    createMix: vi.fn(),
    updateMix: vi.fn(),
    deleteMix: vi.fn(),
    createMaterial: vi.fn(),
    updateMaterial: vi.fn(),
    deleteMaterial: vi.fn(),
  },
}));

const created: ConcreteMixOut = {
  id: "created", project_id: "project", method: "simplified", mix_type: "READY_MIX",
  strength_mpa: 10, scm_pct: 5, mix_id_label: null, gwp_a1a3: null,
  volume_m3: 4, emissions_tco2e: 0.25, notes: "note", sort_order: 0,
  materials: [], created_on: null, updated_on: null,
};

describe("useConcreteRegisterActions", () => {
  beforeEach(() => {
    vi.mocked(ConcreteRegisterService.listMixes).mockReset().mockResolvedValue([]);
    vi.mocked(ConcreteRegisterService.createMix).mockReset();
    vi.mocked(ConcreteRegisterService.updateMix).mockReset();
    vi.mocked(ConcreteRegisterService.deleteMix).mockReset().mockResolvedValue(undefined);
    vi.mocked(ConcreteRegisterService.createMaterial).mockReset();
    vi.mocked(ConcreteRegisterService.updateMaterial).mockReset().mockResolvedValue({} as never);
    vi.mocked(ConcreteRegisterService.deleteMaterial).mockReset().mockResolvedValue(undefined);
  });

  it("keeps simplified mix creation payload and maps the created API row", async () => {
    vi.mocked(ConcreteRegisterService.createMix).mockResolvedValue(created);
    const { result } = renderHook(() => {
      const data = useConcreteRegisterData("project");
      const actions = useConcreteRegisterActions({ projectId: "project", ...data });
      return { data, actions };
    });
    await waitFor(() => expect(result.current.data.loading).toBe(false));

    act(() => result.current.actions.addSimplifiedRow());
    act(() => {
      result.current.actions.updateSimplifiedDraft("scmPct", 5);
      result.current.actions.updateSimplifiedDraft("volumeM3", 4);
      result.current.actions.updateSimplifiedDraft("notes", "note");
    });
    await act(async () => { await result.current.actions.saveSimplifiedDraft(); });

    expect(ConcreteRegisterService.createMix).toHaveBeenCalledWith(expect.objectContaining({
      project_id: "project", method: "simplified", mix_type: "READY_MIX",
      strength_mpa: 5, scm_pct: 5, volume_m3: 4, emissions_tco2e: 0, notes: "note",
    }));
    expect(result.current.data.simplifiedRows).toEqual([expect.objectContaining({
      id: "created", scmPct: 5, volumeM3: 4, notes: "note", emissions_tco2e: 0.25,
    })]);
    expect(result.current.actions.simplifiedDraft).toBeNull();
  });

  it("creates and deletes mix designs, materials, and EPD/PCF rows", async () => {
    vi.mocked(ConcreteRegisterService.createMix)
      .mockResolvedValueOnce({ ...created, id: "mix-design-1", method: "mix_design", mix_id_label: "MIX-01" })
      .mockResolvedValueOnce({ ...created, id: "epd-1", method: "epd_pcf", mix_id_label: "EPD-01" });
    vi.mocked(ConcreteRegisterService.createMaterial).mockResolvedValue({
      id: "material-1", concrete_mix_id: "mix-design-1", material_name: "Cement",
      quantity_kg_m3: 280, carbon_factor: 0.8, sort_order: 0, created_on: null, updated_on: null,
    });

    const { result } = renderHook(() => {
      const data = useConcreteRegisterData("project");
      const actions = useConcreteRegisterActions({ projectId: "project", ...data });
      return { data, actions };
    });
    await waitFor(() => expect(result.current.data.loading).toBe(false));

    await act(async () => { await result.current.actions.addMixRow(); });
    expect(ConcreteRegisterService.createMix).toHaveBeenNthCalledWith(1, expect.objectContaining({
      project_id: "project", method: "mix_design",
    }));
    expect(result.current.data.mixRows).toEqual([expect.objectContaining({ id: "mix-design-1", mixId: "MIX-01" })]);

    await act(async () => { await result.current.actions.addMaterial("mix-design-1"); });
    expect(ConcreteRegisterService.createMaterial).toHaveBeenCalledWith("mix-design-1", expect.objectContaining({
      concrete_mix_id: "mix-design-1",
    }));
    expect(result.current.data.materialsMap["mix-design-1"]).toEqual([
      expect.objectContaining({ id: "material-1", materialName: "Cement", quantityKgM3: 280 }),
    ]);

    await act(async () => { await result.current.actions.deleteMaterial("mix-design-1", "material-1"); });
    await act(async () => { await result.current.actions.deleteMixRow("mix-design-1"); });
    expect(result.current.data.materialsMap["mix-design-1"]).toBeUndefined();
    expect(result.current.data.mixRows).toEqual([]);

    await act(async () => { await result.current.actions.addEpdRow(); });
    expect(ConcreteRegisterService.createMix).toHaveBeenNthCalledWith(2, expect.objectContaining({
      project_id: "project", method: "epd_pcf",
    }));
    expect(result.current.data.epdRows).toEqual([expect.objectContaining({ id: "epd-1", mixId: "EPD-01" })]);
    await act(async () => { await result.current.actions.deleteEpdRow("epd-1"); });
    expect(result.current.data.epdRows).toEqual([]);
  });
});
