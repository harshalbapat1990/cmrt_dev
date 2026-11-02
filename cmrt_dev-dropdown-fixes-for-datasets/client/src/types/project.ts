

export type UserStatusType = "Awaiting Approval" | "Not Started" | "In Progress" | "Closed";
export type AdminStatusType = "Awaiting Approval" | "In Draft" | "Approved" | "Closed";

export interface Project {
  id: string;
  projectName: string;
  programName: string;
  category: string;
  emissions: number;
  lastUpdated: string; 
  status: StatusType;
  statusNote: string;
  access: "view" | "edit";
}

// If you want a single union for filtering across both (for component typing)
export type StatusType = UserStatusType | AdminStatusType | "Rejected" | "Reopen Requested" | "Tech Approved";

export const USER_STATUS_OPTIONS = [
  "Not Started",
  "In Progress",
  "Closed",
] as const;

export const ADMIN_STATUS_OPTIONS = [
  "Not Started",
  "In Progress",
  "Closed",
] as const;

export type RoleType = "user" | "Org admin" | "Project admin";
