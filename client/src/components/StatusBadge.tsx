import React from "react";
import  type { StatusType } from "../types/project";

const statusClass = (status: StatusType) => {
  switch (status) {
    case "In Progress":
      return "bg-blue-100 text-[#115497]";
    case "In Draft":
      return "bg-blue-100 text-blue-700";
    case "Approved":
      return "bg-green-100 text-green-700";
    case "Tech Approved":
      return "bg-blue-100 text-blue-700";
    case "Closed":
      return "bg-gray-200 text-gray-700";
    case "Awaiting Approval":
      return "bg-[#EEE8F8] text-[#5A3A80]";
    case 'Not Started':
      return "bg-[#F7EFD4] text-[#8A5F19]";
    case 'Rejected':
      return "bg-red-100 text-red-700";
    case 'Reopen Requested':
      return "bg-orange-100 text-orange-700";
    default:
      return "bg-[#F7EFD4] text-[#8A5F19]" 
  }
};

export const StatusBadge: React.FC<{ status: StatusType }> = ({ status }) => {
  return (
    <div className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${statusClass(status)}`}>
      {status}
    </div>
  );
};