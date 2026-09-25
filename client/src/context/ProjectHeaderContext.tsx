import { createContext, useContext, useState, useCallback } from "react";
import type { ReactNode } from "react";

type ProjectHeaderState = {
  projectName: string;
  isSaved: boolean;
  projectId: string;
};

type ProjectHeaderContextValue = ProjectHeaderState & {
  setProjectHeader: (name: string, saved: boolean, id?: string) => void;
  clearProjectHeader: () => void;
};

const ProjectHeaderContext = createContext<ProjectHeaderContextValue>({
  projectName: "",
  isSaved: false,
  projectId: "",
  setProjectHeader: () => {},
  clearProjectHeader: () => {},
});

export function ProjectHeaderProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ProjectHeaderState>({ projectName: "", isSaved: false, projectId: "" });

  const setProjectHeader = useCallback((name: string, saved: boolean, id?: string) => {
    setState({ projectName: name, isSaved: saved, projectId: id ?? "" });
  }, []);

  const clearProjectHeader = useCallback(() => {
    setState({ projectName: "", isSaved: false, projectId: "" });
  }, []);

  return (
    <ProjectHeaderContext.Provider value={{ ...state, setProjectHeader, clearProjectHeader }}>
      {children}
    </ProjectHeaderContext.Provider>
  );
}

export function useProjectHeader() {
  return useContext(ProjectHeaderContext);
}
