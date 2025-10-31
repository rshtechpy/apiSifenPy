"""
Ejemplo de uso de la API SIFEN con Redis Cache
Este script demuestra cómo el cache mejora el rendimiento
"""
import asyncio
import aiohttp
import time
from typing import Optional


class SIFENAPIClient:
    """Cliente simple para probar la API SIFEN con cache"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def consultar_ruc(self, ruc: str) -> Optional[dict]:
        """Consultar RUC"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/api/ruc/{ruc}") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Error {response.status}: {await response.text()}")
                        return None
            except Exception as e:
                print(f"Error consultando RUC: {e}")
                return None
    
    async def consultar_dte(self, cdc: str) -> Optional[dict]:
        """Consultar DTE"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/api/dte/{cdc}") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Error {response.status}: {await response.text()}")
                        return None
            except Exception as e:
                print(f"Error consultando DTE: {e}")
                return None
    
    async def health_check(self) -> Optional[dict]:
        """Verificar estado de la API"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
            except Exception as e:
                print(f"Error en health check: {e}")
                return None
    
    async def clear_cache(self, tipo: str, identificador: str = None) -> Optional[dict]:
        """Limpiar cache"""
        async with aiohttp.ClientSession() as session:
            try:
                if tipo == "all":
                    url = f"{self.base_url}/api/cache/all"
                elif tipo == "ruc" and identificador:
                    url = f"{self.base_url}/api/cache/ruc/{identificador}"
                elif tipo == "dte" and identificador:
                    url = f"{self.base_url}/api/cache/dte/{identificador}"
                else:
                    return None
                
                async with session.delete(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
            except Exception as e:
                print(f"Error limpiando cache: {e}")
                return None


async def demo_performance():
    """Demostración del impacto del cache en el rendimiento"""
    print("🚀 Demostración de Redis Cache para SIFEN API")
    print("=" * 60)
    
    client = SIFENAPIClient()
    
    # Verificar que la API esté disponible
    print("🔍 Verificando estado de la API...")
    health = await client.health_check()
    
    if not health:
        print("❌ La API no está disponible. Ejecuta: uvicorn main:app --reload")
        return
    
    print(f"✅ API disponible - Ambiente: {health.get('ambiente')}")
    
    redis_status = health.get('redis', {})
    print(f"📦 Redis: {redis_status.get('status', 'desconocido')}")
    
    if redis_status.get('status') != 'connected':
        print("⚠️  Redis no está conectado - Las pruebas mostrarán solo tiempos sin cache")
    
    print("\n" + "=" * 60)
    
    # RUC de prueba (usar uno válido para mejores resultados)
    test_ruc = "1011758"  # Cambia por un RUC que sepas que existe
    
    print(f"🔍 Probando consulta RUC: {test_ruc}")
    
    # Primera consulta (sin cache)
    print("\n1️⃣  Primera consulta (sin cache)...")
    start_time = time.time()
    result1 = await client.consultar_ruc(test_ruc)
    first_time = time.time() - start_time
    
    if result1:
        print(f"   ✅ Respuesta recibida en {first_time:.3f}s")
        print(f"   📋 Razón Social: {result1.get('data', {}).get('razon_social', 'N/A')}")
    else:
        print("   ❌ Error en la consulta")
        return
    
    # Segunda consulta (con cache)
    print("\n2️⃣  Segunda consulta (con cache)...")
    start_time = time.time()
    result2 = await client.consultar_ruc(test_ruc)
    second_time = time.time() - start_time
    
    if result2:
        print(f"   ✅ Respuesta recibida en {second_time:.3f}s")
        
        # Calcular mejora
        if first_time > 0 and second_time > 0:
            improvement = ((first_time - second_time) / first_time) * 100
            speedup = first_time / second_time if second_time > 0 else 0
            
            print(f"\n📊 Resultados del Cache:")
            print(f"   🐌 Sin cache: {first_time:.3f}s")
            print(f"   ⚡ Con cache: {second_time:.3f}s")
            print(f"   🚀 Mejora: {improvement:.1f}% ({speedup:.1f}x más rápido)")
    else:
        print("   ❌ Error en la consulta")
    
    # Múltiples consultas para mostrar consistencia
    print("\n3️⃣  Múltiples consultas con cache...")
    times = []
    for i in range(5):
        start_time = time.time()
        result = await client.consultar_ruc(test_ruc)
        query_time = time.time() - start_time
        times.append(query_time)
        print(f"   Consulta {i+1}: {query_time:.3f}s")
    
    avg_cache_time = sum(times) / len(times)
    print(f"   📊 Tiempo promedio con cache: {avg_cache_time:.3f}s")
    
    # Limpiar cache para nueva prueba
    print(f"\n4️⃣  Limpiando cache del RUC {test_ruc}...")
    clear_result = await client.clear_cache("ruc", test_ruc)
    if clear_result:
        print(f"   ✅ {clear_result.get('message', 'Cache limpiado')}")
    
    # Una consulta más sin cache
    print("\n5️⃣  Consulta después de limpiar cache...")
    start_time = time.time()
    result3 = await client.consultar_ruc(test_ruc)
    third_time = time.time() - start_time
    
    if result3:
        print(f"   ✅ Respuesta recibida en {third_time:.3f}s")
        print("   📝 Nota: Ahora el resultado se cachea nuevamente para futuras consultas")
    
    print("\n" + "=" * 60)
    print("🎯 Conclusiones:")
    print("   • El cache Redis mejora significativamente el tiempo de respuesta")
    print("   • Las consultas subsequentes son mucho más rápidas")
    print("   • Reduce la carga en los servicios de SIFEN")
    print("   • Puedes limpiar cache manualmente cuando sea necesario")
    print("   • El cache expira automáticamente según la configuración TTL")


async def demo_management():
    """Demostración de gestión de cache"""
    print("\n🛠️  Funciones de Gestión de Cache")
    print("=" * 60)
    
    client = SIFENAPIClient()
    
    # Crear algunos datos de cache
    test_ruc = "1011758"
    print(f"📦 Creando cache para RUC {test_ruc}...")
    await client.consultar_ruc(test_ruc)
    
    # Verificar health con info de Redis
    print("\n📊 Estado actual del sistema:")
    health = await client.health_check()
    if health and health.get('redis'):
        redis_info = health['redis']
        print(f"   Redis Status: {redis_info.get('status')}")
        print(f"   Redis Version: {redis_info.get('version')}")
        print(f"   Used Memory: {redis_info.get('used_memory')}")
    
    # Limpiar cache específico
    print(f"\n🗑️  Limpiando cache específico del RUC {test_ruc}...")
    result = await client.clear_cache("ruc", test_ruc)
    if result:
        print(f"   ✅ {result.get('message')}")
    
    # Crear más datos de cache
    print("\n📦 Creando más datos de cache...")
    await client.consultar_ruc(test_ruc)
    await client.consultar_ruc("1234567")  # Este probablemente no exista
    
    # Limpiar todo el cache
    print("\n🗑️  Limpiando todo el cache...")
    result = await client.clear_cache("all")
    if result:
        print(f"   ✅ {result.get('message')}")
        print(f"   📊 RUCs eliminados: {result.get('deleted_ruc', 0)}")
        print(f"   📊 DTEs eliminados: {result.get('deleted_dte', 0)}")
        print(f"   📊 Total eliminado: {result.get('total_deleted', 0)}")


async def main():
    """Función principal"""
    try:
        await demo_performance()
        await demo_management()
        
        print("\n🎉 Demo completado!")
        print("\n💡 Consejos para usar Redis Cache:")
        print("   • Ajusta los TTL en .env según tus necesidades")
        print("   • Usa /health para monitorear Redis")
        print("   • Limpia cache manualmente si necesitas datos actualizados")
        print("   • Redis mejora mucho el rendimiento en producción")
        
    except Exception as e:
        print(f"❌ Error en la demo: {e}")


if __name__ == "__main__":
    # Instalar aiohttp si no está instalado:
    # pip install aiohttp
    
    print("⚠️  Asegúrate de que la API esté ejecutándose:")
    print("    uvicorn main:app --reload")
    print("")
    
    asyncio.run(main())