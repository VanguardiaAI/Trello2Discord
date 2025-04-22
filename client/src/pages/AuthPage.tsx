import { useState } from "react";
import { LoginForm } from "../components/auth/LoginForm";
import { RegisterForm } from "../components/auth/RegisterForm";
import { Alert } from '../components/ui/alert';

function TempPasswordView({ onSuccess }: { onSuccess: () => void }) {
  const [tempPassword, setTempPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tempPassword === "Workana2025") {
      setError("");
      onSuccess();
    } else {
      setError("Contraseña temporal incorrecta");
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <div className="fixed top-0 left-0 w-full h-2 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 z-40" />
      <div className="space-y-6 w-full max-w-md bg-white rounded-xl shadow-lg p-8 pt-10 relative z-50 mt-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Contraseña temporal</h1>
          <p className="text-sm text-gray-500 mt-2">
            Ingresa la contraseña temporal para poder registrarte
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="tempPassword" className="block text-sm font-medium text-gray-700">Contraseña temporal</label>
            <input
              id="tempPassword"
              type="password"
              className="w-full border border-gray-300 rounded px-3 py-2"
              value={tempPassword}
              onChange={(e) => setTempPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="w-full bg-black text-white py-2 rounded hover:bg-gray-900">Continuar</button>
        </form>
      </div>
    </div>
  );
}

export function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [showRegister, setShowRegister] = useState(false);

  const handleLogin = async (email: string, password: string) => {
    try {
      const response = await fetch('http://localhost:5000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Error al iniciar sesión');
      }

      // Guardar token en localStorage
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      // Redireccionar al dashboard o página principal
      window.location.href = '/dashboard';
    } catch (error) {
      setAlert({ type: 'error', message: 'Error al iniciar sesión. Por favor, intenta de nuevo.' });
    }
  };

  const handleRegister = async (name: string, email: string, password: string, tempPassword: string) => {
    try {
      const response = await fetch('http://localhost:5000/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, password, temp_password: tempPassword }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Error al registrarse');
      }

      setIsLogin(true);
      setAlert({ type: 'success', message: '¡Registro exitoso! Ahora puedes iniciar sesión.' });
    } catch (error) {
      setAlert({ type: 'error', message: 'Error al registrarse. Por favor, intenta de nuevo.' });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      {alert && (
        <Alert
          variant={alert.type === 'success' ? 'success' : 'error'}
          title={alert.type === 'success' ? 'Éxito' : 'Error'}
          description={alert.message}
          onClose={() => setAlert(null)}
          className="mb-4"
        />
      )}
      {isLogin ? (
        <LoginForm 
          onLogin={handleLogin} 
          onSwitchToRegister={() => setIsLogin(false)} 
        />
      ) : showRegister ? (
        <RegisterForm 
          onRegister={(name, email, password) => handleRegister(name, email, password, "Workana2025")}
          onSwitchToLogin={() => { setIsLogin(true); setShowRegister(false); }} 
        />
      ) : (
        <TempPasswordView onSuccess={() => setShowRegister(true)} />
      )}
    </div>
  );
} 