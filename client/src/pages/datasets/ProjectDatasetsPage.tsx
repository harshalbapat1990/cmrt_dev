import { useParams } from 'react-router-dom';
import DatasetsPage from './DatasetsPage';
import { useUser } from '@/context/UserContext';


export default function ProjectDatasetsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { user } = useUser();
  const orgId = user?.organisation_id;

  if (!projectId) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        No project ID provided.
      </div>
    );
  }

  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        No organisation found for your account.
      </div>
    );
  }

  return <DatasetsPage scope={{ type: 'PROJECT', projectId, orgId }} />;
}
