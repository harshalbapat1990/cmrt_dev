import React from "react";
import ProjectsPage from "./ProjectsPage";
import type { Project } from "../../../types/project";

interface Props {
  data: Project[];
}

const UserProjects: React.FC<Props> = ({ data }) => {
  return (
    <ProjectsPage
      role="user"
      data={data}
      showRequestAccessButton={true}
    />
  );
};

export default UserProjects;