import { ReactNode } from 'react';
import Navbar from './ui/Navbar';

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      <main className="flex-grow pt-24 px-4">
        {children}
      </main>
      <footer className="bg-white border-t border-gray-200 py-6 mt-auto">
        <div className="px-4 md:px-6">
          <p className="text-center text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} Brandoon. Todos los derechos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout; 