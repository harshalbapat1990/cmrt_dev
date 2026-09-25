import DatasetsPage from './DatasetsPage';
import { useUser } from '@/context/UserContext';


export default function OrgDatasetsPage() {
  const { user } = useUser();
  const orgId = user?.organisation_id;

  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        No organisation found for your account.
      </div>
    );
  }

  return <DatasetsPage scope={{ type: 'ORG', orgId }} />;
}
