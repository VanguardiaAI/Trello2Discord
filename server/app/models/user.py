import bcrypt
from datetime import datetime
from bson import ObjectId

class User:
    def __init__(self, name, email, password, created_at=None, _id=None):
        self.name = name
        self.email = email
        self.password = self._hash_password(password) if not isinstance(password, bytes) else password
        self.created_at = created_at or datetime.utcnow()
        self._id = _id

    def _hash_password(self, password):
        """Hash de la contraseña usando bcrypt"""
        if isinstance(password, str):
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return password

    def check_password(self, password):
        """Verificar si la contraseña proporcionada coincide con el hash"""
        if not self.password:
            return False
        if isinstance(password, str):
            password = password.encode('utf-8')
        return bcrypt.checkpw(password, self.password)

    def to_dict(self):
        """Convertir el objeto a un diccionario para JSON/MongoDB"""
        return {
            "_id": str(self._id) if self._id else None,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        """Crear un objeto User a partir de un diccionario"""
        if not data:
            return None
        
        # Manejar el caso en que _id pueda ser un ObjectId o un string
        _id = data.get('_id')
        if _id and not isinstance(_id, ObjectId):
            try:
                _id = ObjectId(_id)
            except:
                pass
                
        return cls(
            name=data.get('name'),
            email=data.get('email'),
            password=data.get('password'),
            created_at=data.get('created_at'),
            _id=_id
        )

    def save(self, db):
        """Guardar el usuario en la base de datos"""
        user_data = {
            "name": self.name,
            "email": self.email,
            "password": self.password,
            "created_at": self.created_at
        }
        
        if not self._id:
            result = db.users.insert_one(user_data)
            self._id = result.inserted_id
        else:
            db.users.update_one({"_id": self._id}, {"$set": user_data})
        
        return self

    @classmethod
    def find_by_email(cls, email, db):
        """Encontrar usuario por email"""
        user_data = db.users.find_one({"email": email})
        return cls.from_dict(user_data) if user_data else None

    @classmethod
    def find_by_id(cls, id, db):
        """Encontrar usuario por ID"""
        if isinstance(id, str):
            try:
                id = ObjectId(id)
            except:
                return None
        user_data = db.users.find_one({"_id": id})
        return cls.from_dict(user_data) if user_data else None 