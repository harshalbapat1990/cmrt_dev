// /src/types/access.ts
export type AccessLevel = "View" | "Edit";

export type StageAccess = {
  name: string; // e.g., "Business case" | "Design" | "Construction" | "N/A"
  access: AccessLevel;
};

export type AdminAccessRequest = {
  id: string;
  requester: string;
  projectName: string;
  projectCategory: string;
  stages: StageAccess[];
  dateRequested: string;
  justification?: string;
  requestedRole?: string;
};

export type SuperAdminAccessRequest = {
  id: string;
  requestType?: string;
  requestedBy: string;
  email: string;
  organisation: string;
  dateRequested: string;
  reason?: string | null;
  action?: string;
};

export type OrgAdminAccessRequest = {
  id: string;
  requestedBy: string;
  email: string;
  projectName: string;
  dateRequested: string;
  justification: string | null;
  requestedRole: string;
  action?: string;
};

export type ProjectAdminAccessRequest = {
  id: string;
  requestedBy: string;
  email: string;
  projectName: string;
  dateRequested: string; 
  justification?: string;
  action?: string;
};


export type MemberAssignment = {
  stage: StageAccess;
  access: AccessLevel;
};

export type ProjectMember = {
  id: string;
  name: string;
  email: string;
  assignments: MemberAssignment[];
};

export type ProjectRow = {
  id: string;
  name: string;
  program: string;
  category: "Small" | "Large" | "Recurring";
  users: number;
  dateCreated: string; // ISO
  members: ProjectMember[];
};
