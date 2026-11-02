import React from "react";
import ProjectsPage from "../projects/ProjectsPage";
import type { Project, RoleType } from "../../../types/project";

interface Props {
  data: Project[];
  role: RoleType;
}

const AdminProjects: React.FC<Props> = ({ data, role }) => {

  return (
    <ProjectsPage
      role={role}
      data={data}
      showRequestAccessButton={role === "Project admin" ? true : false}
      showProjectCreationButton={role === "Project admin" ? false : true}
      
    />
  );
};

export default AdminProjects;
