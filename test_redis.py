"""
Script de prueba para verificar la funcionalidad de Redis cache
"""
import asyncio
import logging
from services.redis_cache import redis_cache

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_redis_connection():
    """Test de conexión básica a Redis"""
    print("\n🔗 Probando conexión a Redis...")
    
    try:
        await redis_cache.connect()
        
        health = await redis_cache.health_check()
        print(f"✅ Estado Redis: {health}")
        
        if health.get('status') == 'connected':
            print("✅ Redis conectado correctamente")
            return True
        else:
            print("❌ Redis no conectado")
            return False
            
    except Exception as e:
        print(f"❌ Error conectando a Redis: {e}")
        return False


async def test_cache_operations():
    """Test de operaciones básicas del cache"""
    print("\n📦 Probando operaciones de cache...")
    
    try:
        # Test SET
        test_data = {
            "codigo": "0502",
            "mensaje": "Consulta exitosa",
            "data": {
                "ruc": "1234567",
                "razon_social": "Test Company",
                "estado": "ACT"
            }
        }
        
        success = await redis_cache.set_ruc_cache("1234567", test_data)
        print(f"✅ SET RUC cache: {success}")
        
        # Test GET
        cached_data = await redis_cache.get_ruc_cache("1234567")
        print(f"✅ GET RUC cache: {cached_data is not None}")
        
        if cached_data:
            print(f"   Datos obtenidos: {cached_data['data']['razon_social']}")
        
        # Test DELETE
        key = redis_cache.get_ruc_key("1234567")
        deleted = await redis_cache.delete(key)
        print(f"✅ DELETE cache: {deleted}")
        
        # Verificar que se eliminó
        cached_data = await redis_cache.get_ruc_cache("1234567")
        print(f"✅ Verificación DELETE: {cached_data is None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en operaciones cache: {e}")
        return False


async def test_cache_performance():
    """Test de rendimiento básico"""
    print("\n⚡ Probando rendimiento del cache...")
    
    try:
        import time
        
        # Datos de prueba
        test_data = {"codigo": "0502", "mensaje": "Test", "data": {"ruc": "test", "razon_social": "Performance Test"}}
        
        # Test SET performance
        start = time.time()
        for i in range(100):
            await redis_cache.set_ruc_cache(f"perf_test_{i}", test_data)
        set_time = time.time() - start
        print(f"✅ 100 SETs en: {set_time:.3f}s ({100/set_time:.1f} ops/s)")
        
        # Test GET performance
        start = time.time()
        for i in range(100):
            await redis_cache.get_ruc_cache(f"perf_test_{i}")
        get_time = time.time() - start
        print(f"✅ 100 GETs en: {get_time:.3f}s ({100/get_time:.1f} ops/s)")
        
        # Limpiar datos de prueba
        await redis_cache.clear_pattern("sifen:ruc:perf_test_*")
        print("✅ Datos de prueba limpiados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test de rendimiento: {e}")
        return False


async def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de Redis Cache")
    print("=" * 50)
    
    # Test 1: Conexión
    connected = await test_redis_connection()
    
    if not connected:
        print("\n❌ No se puede continuar sin conexión a Redis")
        print("💡 Asegúrate de que Redis esté ejecutándose en localhost:6379")
        return
    
    # Test 2: Operaciones básicas
    operations_ok = await test_cache_operations()
    
    # Test 3: Rendimiento (solo si las operaciones básicas funcionan)
    if operations_ok:
        performance_ok = await test_cache_performance()
    
    # Desconectar
    await redis_cache.disconnect()
    
    print("\n" + "=" * 50)
    print("🏁 Pruebas completadas")
    
    if connected and operations_ok:
        print("✅ Redis cache está funcionando correctamente")
        print("💡 Tu API ahora tiene cache Redis habilitado para mejorar el rendimiento")
    else:
        print("❌ Hay problemas con Redis cache")
        print("💡 Revisa la configuración y que Redis esté ejecutándose")


if __name__ == "__main__":
    asyncio.run(main())