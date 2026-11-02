import React from "react";
import type { Project } from "../types/project";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "./StatusBadge";

type SortDir = "asc" | "desc";

interface Props {
  projects: Project[];
  sortDir: SortDir;
  role: string; // e.g., "admin" | "user"
  onSortChange: (dir: SortDir) => void;
}

const ProjectTable: React.FC<Props> = ({ projects, sortDir, onSortChange, role }) => {
  const toggleSort = () => onSortChange(sortDir === "asc" ? "desc" : "asc");
  const navigate = useNavigate();

  // Centralized action to plug API or navigation later
  const handleRowAction = async (project: Project) => {
    // TODO: Call your API / or navigate once available
    // Example:
    // try {
    //   const res = await fetch(`/api/projects/${project.id}`);
    //   const data = await res.json();
    navigate(`/projects/${project.id}`);
    // } catch (e) {
    //   console.error("Failed to open project", e);
    // }
  };

  return (
    
<div
    className="overflow-y-auto scroll-styled"
    style={{ maxHeight: "calc(100vh - 300px)" }}
  >
    <table
      className="min-w-full text-sm border-separate"
      style={{ borderSpacing: 0 }}
    >
     
      <thead className="bg-gray-50 border-y border-gray-200 text-gray-700 text-xs sticky top-0 z-10">
        <tr>
          <th className="px-6 py-3 text-left uppercase tracking-wide">
            Project Name
          </th>
          <th className="px-6 py-3 text-left uppercase tracking-wide">
            Project Category
          </th>

          <th className="px-6 py-3 text-left uppercase tracking-wide">
            <button
              type="button"
              onClick={toggleSort}
              className="flex items-center gap-1 cursor-pointer"
            >
              <span>Last Modified</span>
              <span className="material-symbols-rounded">
                {sortDir === "desc"
                  ? "arrow_drop_down"
                  : "arrow_drop_up"}
              </span>
            </button>
          </th>

          <th className="px-6 py-3 text-left uppercase tracking-wide">
            Status
          </th>
        </tr>
      </thead>

      <tbody>
        {projects.map((project) => {
          const isRowClickable =
            role === "admin" || project.access === "view" || project.access === "edit";

          return (
            <tr
              key={project.id}
              className={`group border-b border-gray-200 transition-colors ${
                isRowClickable ? "hover:bg-gray-50 cursor-pointer" : ""
              }`}
              onClick={
                isRowClickable
                  ? () => handleRowAction(project)
                  : undefined
              }
            >
              <td className="px-6 py-4">
                <div className="flex items-center gap-2 font-medium">
                  <span
                    className={`text-gray-800 ${
                      isRowClickable
                        ? "group-hover:text-primary"
                        : ""
                    }`}
                  >
                    {project.projectName}
                  </span>

                  {role !== "admin" && project.access === "view" && (
                    <span className="material-symbols-rounded text-gray-400 text-xs">
                      lock
                    </span>
                  )}
                </div>

                <div className="text-xs text-gray-500">
                  {project.programName}
                </div>
              </td>

              <td className="px-6 py-4 text-gray-700">
                {project.category}
              </td>

              <td className="px-6 py-4 text-gray-700">
                {project.lastUpdated
                  ? new Date(project.lastUpdated).toLocaleDateString(
                      "en-GB",
                      {
                        day: "2-digit",
                        month: "long",
                        year: "numeric",
                      }
                    )
                  : "-"}
              </td>

              <td className="px-6 py-4">
                <StatusBadge status={project.status} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  </div>

  );
};

export default ProjectTable;