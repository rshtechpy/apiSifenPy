"""
Test específico para verificar la serialización de modelos Pydantic en Redis
"""
import asyncio
import logging
from services.redis_cache import redis_cache
from models.schemas import RUCData, DTEData

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_pydantic_serialization():
    """Probar serialización de modelos Pydantic"""
    print("🧪 Probando serialización de modelos Pydantic...")
    
    try:
        # Conectar a Redis
        await redis_cache.connect()
        
        # Crear datos de prueba con modelos Pydantic
        ruc_data = RUCData(
            ruc="1234567",
            razon_social="Test Company S.A.",
            estado="ACT",
            estado_descripcion="ACTIVO",
            es_facturador_electronico=True
        )
        
        # Simular la estructura que devuelve el parser
        parsed_data = {
            "codigo": "0502",
            "mensaje": "Consulta exitosa",
            "data": ruc_data  # Esto es un modelo Pydantic
        }
        
        print(f"📦 Datos originales: {type(parsed_data['data'])}")
        print(f"   RUC: {parsed_data['data'].ruc}")
        print(f"   Razón Social: {parsed_data['data'].razon_social}")
        
        # Intentar guardar en cache (esto debería funcionar ahora)
        success = await redis_cache.set_ruc_cache("1234567", parsed_data)
        print(f"✅ Guardado en cache: {success}")
        
        if success:
            # Intentar recuperar del cache
            cached_data = await redis_cache.get_ruc_cache("1234567")
            print(f"📥 Recuperado del cache: {cached_data is not None}")
            
            if cached_data:
                print(f"   Tipo de datos recuperados: {type(cached_data)}")
                print(f"   Código: {cached_data.get('codigo')}")
                print(f"   Datos RUC: {cached_data.get('data', {})}")
                
                # Verificar que se puede reconstruir el modelo si es necesario
                data_dict = cached_data.get('data', {})
                if isinstance(data_dict, dict) and 'ruc' in data_dict:
                    reconstructed = RUCData(**data_dict)
                    print(f"✅ Modelo reconstruido: {reconstructed.ruc} - {reconstructed.razon_social}")
        
        # Limpiar
        await redis_cache.delete(redis_cache.get_ruc_key("1234567"))
        print("🗑️ Datos de prueba limpiados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        logger.error(f"Error detallado: {e}", exc_info=True)
        return False
    
    finally:
        await redis_cache.disconnect()


async def test_complex_dte_data():
    """Probar con datos DTE más complejos"""
    print("\n🧪 Probando datos DTE complejos...")
    
    try:
        await redis_cache.connect()
        
        # Simular datos DTE complejos (esto es lo que probablemente esté causando el error)
        from models.schemas import EmisorData, ReceptorData, ItemData, TotalesData
        
        emisor = EmisorData(
            ruc="1234567-8",
            nombre="Empresa Test",
            direccion="Dirección Test 123"
        )
        
        receptor = ReceptorData(
            nombre="Cliente Test",
            tipo_id="Cédula de identidad civil",
            numero_id="12345678"
        )
        
        item = ItemData(
            codigo="PROD001",
            descripcion="Producto de prueba",
            cantidad=2.0,
            precio_unitario=5000.0,
            total=10000
        )
        
        totales = TotalesData(
            total_operacion=10000,
            total_iva=476,
            moneda="PYG"
        )
        
        dte_data = DTEData(
            cdc="01234567890123456789012345678901234567890123",
            numero_autorizacion="12345678901",
            fecha_emision="2025-10-31T15:30:00",
            tipo_documento="Factura electrónica",
            emisor=emisor,
            receptor=receptor,
            totales=totales,
            items=[item]
        )
        
        parsed_dte = {
            "codigo": "0422",
            "mensaje": "Documento encontrado",
            "data": dte_data  # Modelo Pydantic complejo con objetos anidados
        }
        
        print(f"📦 DTE con objetos anidados: {type(dte_data)}")
        print(f"   Emisor: {type(dte_data.emisor)} - {dte_data.emisor.nombre}")
        print(f"   Items: {len(dte_data.items)} item(s)")
        
        # Intentar guardar (aquí era donde ocurría el error)
        success = await redis_cache.set_dte_cache("01234567890123456789012345678901234567890123", parsed_dte)
        print(f"✅ DTE guardado en cache: {success}")
        
        if success:
            cached_dte = await redis_cache.get_dte_cache("01234567890123456789012345678901234567890123")
            print(f"📥 DTE recuperado: {cached_dte is not None}")
            
            if cached_dte:
                data_dict = cached_dte.get('data', {})
                print(f"   Emisor recuperado: {data_dict.get('emisor', {}).get('nombre')}")
                print(f"   Items recuperados: {len(data_dict.get('items', []))}")
        
        # Limpiar
        await redis_cache.delete(redis_cache.get_dte_key("01234567890123456789012345678901234567890123"))
        print("🗑️ Datos DTE limpiados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test DTE: {e}")
        logger.error(f"Error detallado DTE: {e}", exc_info=True)
        return False
    
    finally:
        await redis_cache.disconnect()


async def main():
    """Ejecutar todas las pruebas"""
    print("🚀 Test de Serialización Pydantic con Redis")
    print("=" * 50)
    
    # Test 1: RUC simple
    ruc_ok = await test_pydantic_serialization()
    
    # Test 2: DTE complejo
    dte_ok = await test_complex_dte_data()
    
    print("\n" + "=" * 50)
    if ruc_ok and dte_ok:
        print("✅ Todos los tests pasaron - La serialización está corregida")
    else:
        print("❌ Algunos tests fallaron - Revisar la implementación")


if __name__ == "__main__":
    asyncio.run(main())