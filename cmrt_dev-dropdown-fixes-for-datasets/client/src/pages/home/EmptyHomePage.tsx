import { useNavigate } from "react-router-dom";
import EmptyFolderUrl from "../../assets/icons/emptyproject.svg";
import { useState } from "react";
import ProjectAccess from "../../components/ProjectAccess";
import { Modal } from "../../components/common/Modal";

type OverviewProps = {
  role: string;
};

export default function EmptHomePage({ role }: OverviewProps) {
  const navigate = useNavigate();
  const [showRequestAccess, setShowRequestAccess] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const openRequestModal = () => setShowRequestAccess(true);
  const closeRequestModal = () => setShowRequestAccess(false);
  const openCancelModal = () => setShowCancelConfirm(true);
  const closeCancelModal = () => setShowCancelConfirm(false);

  const closeAllModals = () => {
    setShowRequestAccess(false);
    setShowCancelConfirm(false);
  };

  if (role === "admin") {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center">
        <img src={EmptyFolderUrl} alt="empty project" className="mb-6" />
        <p className="text-2xl text-text-base mb-4 ">You have no projects</p>
        <p className="mb-6 max-w-100 text-base text-gray-600 text-wrap">
          Get started by creating your first project
        </p>
        <button
          className="cursor-pointer rounded-[var(--radius-3)] border-0 bg-primary px-4 py-2.5 text-white transition-colors hover:brightness-95 mt-3"
          onClick={() => {
            navigate("/AddNewProject");
          }}
          type="button"
        >
          Create Project
        </button>
      </div>
    );
  }
  return (
    <>
      <div className="flex flex-col items-center justify-center h-screen text-center">
        <img src={EmptyFolderUrl} alt="empty project" className="mb-6" />
        <p className="text-2xl mb-4 text-text-base">
          You don't have access to any projects yet
        </p>
        <p className="mb-6 max-w-100 text-base text-gray-600 text-wrap">
          To get started, request access to an existing project. Your administrator will review and
          approve your request.
        </p>
        <button
          className="cursor-pointer rounded-[var(--radius-3)] border-0 bg-primary px-4 py-2.5 text-white transition-colors hover:brightness-95 mt-3"
          onClick={openRequestModal}
          type="button"
        >
          Request project Access
        </button>
      </div>

      <Modal isOpen={showRequestAccess} onClose={closeRequestModal} className="max-w-150 p-6">
        <ProjectAccess
          onCloseRequestModal={() => {
            closeRequestModal();
          }}
          onOpenCancelModal={() => {
            openCancelModal();
          }}
          onCloseAllModals={() => {
            closeAllModals();
          }}
        />
      </Modal>

      <Modal isOpen={showCancelConfirm} onClose={closeCancelModal} className="max-w-150 p-6">
        <div className="bg-white p-2 sm:p-4">
          <div className="text-lg sm:text-2xl text-text-dark font-medium">Discard changes?</div>
          <div className="mt-3 sm:mt-4 text-sm text-text-base">
            Are you sure you want to discard your changes?
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <button
              className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95"
              type="button"
              onClick={() => {
                closeCancelModal();
                openRequestModal();
              }}
            >
              Keep editing
            </button>
            <button
              className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95"
              type="button"
              onClick={closeAllModals}
            >
              Discard changes
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}