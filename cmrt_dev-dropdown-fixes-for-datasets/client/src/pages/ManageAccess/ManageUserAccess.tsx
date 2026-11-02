

import AdminAccessPage from './AdminAccessPage';
import SuperAdminAccessPage from './SuperAdminAccessPage';
import OrgAdminAccessPage from './OrgAdminAccess';

type Props = {
  role: "superadmin" | "admin" | "orgadmin";
}


export default function ManageUserAccess({role}:Props) {

    switch(role){
        case "admin":
            return <AdminAccessPage />  
        case "superadmin":
            return <SuperAdminAccessPage />
        case "orgadmin":
            return <OrgAdminAccessPage />
        default:
            return <div>Invalid role</div>
    }

} 