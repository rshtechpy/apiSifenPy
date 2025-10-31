"""
Test simple de serialización sin dependencias complejas
"""
import json
from typing import Any


def serialize_value(value: Any) -> str:
    """Serializa valores para Redis, manejando modelos Pydantic"""
    try:
        # Si es un diccionario, intentar serializar directamente
        if isinstance(value, dict):
            # Convertir cualquier modelo Pydantic en el diccionario
            serializable_dict = {}
            for k, v in value.items():
                if hasattr(v, 'model_dump'):  # Es un modelo Pydantic
                    serializable_dict[k] = v.model_dump()
                elif isinstance(v, (list, tuple)):
                    # Manejar listas que pueden contener modelos Pydantic
                    serializable_dict[k] = [
                        item.model_dump() if hasattr(item, 'model_dump') else item
                        for item in v
                    ]
                else:
                    serializable_dict[k] = v
            return json.dumps(serializable_dict, ensure_ascii=False, default=str)
        
        # Si tiene model_dump (es un modelo Pydantic)
        elif hasattr(value, 'model_dump'):
            return json.dumps(value.model_dump(), ensure_ascii=False, default=str)
        
        # Para otros tipos, usar json.dumps con default=str para manejar tipos no serializables
        else:
            return json.dumps(value, ensure_ascii=False, default=str)
            
    except Exception as e:
        print(f"Error serializando valor: {e}")
        # Fallback: convertir a string
        return json.dumps(str(value), ensure_ascii=False)


# Simular modelo Pydantic simple
class MockRUCData:
    def __init__(self, ruc, razon_social, estado):
        self.ruc = ruc
        self.razon_social = razon_social
        self.estado = estado
    
    def model_dump(self):
        return {
            "ruc": self.ruc,
            "razon_social": self.razon_social,
            "estado": self.estado
        }


def test_serialization():
    """Probar la serialización"""
    print("🧪 Probando serialización...")
    
    # Crear datos de prueba que simulan lo que devuelve el parser
    mock_ruc = MockRUCData("1234567", "Test Company", "ACT")
    
    parsed_data = {
        "codigo": "0502",
        "mensaje": "Éxito",
        "data": mock_ruc  # Modelo Pydantic mock
    }
    
    print(f"📦 Datos originales: {parsed_data}")
    print(f"   Tipo de data: {type(parsed_data['data'])}")
    
    # Serializar
    try:
        serialized = serialize_value(parsed_data)
        print(f"✅ Serialización exitosa:")
        print(f"   {serialized}")
        
        # Deserializar para verificar
        deserialized = json.loads(serialized)
        print(f"✅ Deserialización exitosa:")
        print(f"   Código: {deserialized['codigo']}")
        print(f"   RUC: {deserialized['data']['ruc']}")
        print(f"   Razón Social: {deserialized['data']['razon_social']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Test de Serialización Simple")
    print("=" * 40)
    
    success = test_serialization()
    
    print("=" * 40)
    if success:
        print("✅ La función de serialización funciona correctamente")
        print("💡 El problema debería estar resuelto en Redis")
    else:
        print("❌ Hay problemas con la serialización")