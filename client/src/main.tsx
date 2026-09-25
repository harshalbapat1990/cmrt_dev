import { createRoot } from 'react-dom/client'
import {  RouterProvider } from 'react-router-dom'
import { ToastProvider } from './components/common/ToastProvider'
import { router }  from "./router"
import './index.css'
import "./chartSetup";

createRoot(document.getElementById('root')!).render(
    <ToastProvider>
        <RouterProvider router={router} />
    </ToastProvider>
)

