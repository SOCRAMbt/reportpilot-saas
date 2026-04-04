'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  FileText,
  DollarSign,
  Users,
  Bell,
  Settings,
  Menu,
  X,
  LogOut,
  Archive,
  Calculator,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Comprobantes', href: '/comprobantes', icon: FileText },
  { name: 'VEPs', href: '/veps', icon: DollarSign },
  { name: 'Clientes', href: '/clientes', icon: Users },
  { name: 'Alertas', href: '/alertas', icon: Bell, badge: true },
  { name: 'Bank-Kit', href: '/bank-kit', icon: Archive },
  { name: 'Configuración', href: '/configuracion', icon: Settings },
]

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const pathname = usePathname() || '/'
  const router = useRouter()

  const handleLogout = () => {
    localStorage.removeItem('accountantos_token')
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar móvil */}
      <div className={`fixed inset-0 z-40 lg:hidden ${sidebarOpen ? '' : 'pointer-events-none'}`}>
        <div
          className={`fixed inset-0 bg-gray-600 bg-opacity-75 transition-opacity ${
            sidebarOpen ? 'opacity-100' : 'opacity-0'
          }`}
          onClick={() => setSidebarOpen(false)}
        />

        <div
          className={`fixed inset-y-0 left-0 flex w-64 flex-col bg-white transition-transform ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <SidebarContent pathname={pathname} onLogout={handleLogout} />
        </div>
      </div>

      {/* Sidebar desktop */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex min-h-0 flex-1 flex-col bg-white border-r border-slate-200">
          <SidebarContent pathname={pathname} onLogout={handleLogout} />
        </div>
      </div>

      {/* Contenido principal */}
      <div className="lg:pl-64">
        {/* Header superior */}
        <header className="sticky top-0 z-10 flex h-16 flex-shrink-0 bg-white border-b border-slate-200">
          <button
            type="button"
            className="lg:hidden px-4 text-slate-500"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>

          <div className="flex flex-1 justify-between px-4">
            <div className="flex items-center">
              <h1 className="text-lg font-semibold text-blue-600">AccountantOS v9.7</h1>
            </div>

            <div className="flex items-center space-x-4">
              <button className="text-slate-400 hover:text-slate-500">
                <Bell className="h-6 w-6" />
              </button>
              <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
                A
              </div>
            </div>
          </div>
        </header>

        {/* Contenido de la página */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

function SidebarContent({ pathname, onLogout }: { pathname: string; onLogout: () => void }) {
  return (
    <>
      {/* Logo */}
      <div className="flex h-16 items-center px-6 border-b border-slate-200">
        <Calculator className="h-8 w-8 text-blue-600 mr-2" />
        <span className="text-xl font-bold text-slate-900">AccountantOS</span>
      </div>

      {/* Navegación */}
      <nav className="flex flex-1 flex-col overflow-y-auto p-4">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600 -ml-1 pl-2'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center">
                    <item.icon className="h-5 w-5 mr-3" />
                    {item.name}
                  </div>
                  {item.badge && (
                    <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                      3
                    </span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer del sidebar */}
      <div className="border-t border-slate-200 p-4">
        <button
          onClick={onLogout}
          className="flex w-full items-center px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
        >
          <LogOut className="h-5 w-5 mr-3" />
          Cerrar sesión
        </button>
      </div>
    </>
  )
}
