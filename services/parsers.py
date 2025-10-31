import xml.etree.ElementTree as ET
import html
import xmltodict
import re
from typing import Dict, Any, Optional, List
from models.schemas import (
    RUCData, EmisorData, ReceptorData, 
    ItemData, TotalesData, DTEData
)
import logging

logger = logging.getLogger(__name__)


class XMLParser:
    """Parser para convertir respuestas XML de SIFEN a objetos Python"""
    
    # Namespaces de SIFEN
    NS = {
        'env': 'http://www.w3.org/2003/05/soap-envelope',
        'ns2': 'http://ekuatia.set.gov.py/sifen/xsd'
    }
    
    @staticmethod
    def parse_ruc_response(xml_response: str) -> Dict[str, Any]:
        """
        Parsear respuesta de consulta RUC
        
        Returns:
            Dict con codigo, mensaje y data (si existe)
        """
        try:
            logger.debug(f"Parseando XML Response: {xml_response[:500]}...")
            
            # Limpiar el XML de caracteres problemáticos
            xml_clean = xml_response.strip()
            
            # Intentar parsear el XML
            root = ET.fromstring(xml_clean)
            
            # Buscar el body de la respuesta
            body = root.find('.//ns2:rResEnviConsRUC', XMLParser.NS)
            
            if body is None:
                logger.error("No se encontró el elemento rResEnviConsRUC en la respuesta")
                logger.debug(f"XML completo: {xml_response}")
                raise ValueError("Respuesta XML inválida - No se encontró rResEnviConsRUC")
            
            # Extraer código y mensaje
            codigo_elem = body.find('ns2:dCodRes', XMLParser.NS)
            mensaje_elem = body.find('ns2:dMsgRes', XMLParser.NS)
            
            if codigo_elem is None or mensaje_elem is None:
                raise ValueError("Respuesta XML inválida - Faltan elementos requeridos")
            
            codigo = codigo_elem.text
            mensaje = mensaje_elem.text
            
            result = {
                'codigo': codigo,
                'mensaje': mensaje,
                'data': None
            }
            
            logger.info(f"Respuesta parseada - Código: {codigo}, Mensaje: {mensaje}")
            
            # Si código es 0502 (éxito), extraer datos
            if codigo == '0502':
                cont_ruc = body.find('.//ns2:xContRUC', XMLParser.NS)
                
                if cont_ruc is not None:
                    ruc_data = RUCData(
                        ruc=cont_ruc.find('ns2:dRUCCons', XMLParser.NS).text,
                        razon_social=cont_ruc.find('ns2:dRazCons', XMLParser.NS).text.strip(),
                        estado=cont_ruc.find('ns2:dCodEstCons', XMLParser.NS).text,
                        estado_descripcion=cont_ruc.find('ns2:dDesEstCons', XMLParser.NS).text,
                        es_facturador_electronico=cont_ruc.find('ns2:dRUCFactElec', XMLParser.NS).text == 'S'
                    )
                    result['data'] = ruc_data
                    logger.info(f"Datos RUC extraídos: {ruc_data.ruc} - {ruc_data.razon_social}")
            
            return result
            
        except ET.ParseError as e:
            logger.error(f"Error de parseo XML: {e}")
            logger.error(f"XML que causó el error: {xml_response}")
            raise Exception(f"XML mal formado: {str(e)}")
        except Exception as e:
            logger.error(f"Error parseando respuesta RUC: {e}")
            logger.error(f"XML completo: {xml_response}")
            raise
    
    @staticmethod
    def parse_dte_response(xml_response: str) -> Dict[str, Any]:
        """
        Parsear respuesta de consulta DTE
        
        Returns:
            Dict con codigo, mensaje y data (si existe)
        """
        try:
            logger.debug(f"Parseando XML Response DTE: {xml_response[:500]}...")
            
            # Limpiar el XML de caracteres problemáticos
            xml_clean = xml_response.strip()
            
            root = ET.fromstring(xml_clean)
            
            # Buscar el body de la respuesta
            body = root.find('.//ns2:rEnviConsDeResponse', XMLParser.NS)
            
            if body is None:
                logger.error("No se encontró el elemento rEnviConsDeResponse en la respuesta")
                logger.debug(f"XML completo: {xml_response}")
                raise ValueError("Respuesta XML inválida - No se encontró rEnviConsDeResponse")
            
            # Extraer código y mensaje
            codigo_elem = body.find('ns2:dCodRes', XMLParser.NS)
            mensaje_elem = body.find('ns2:dMsgRes', XMLParser.NS)
            
            if codigo_elem is None or mensaje_elem is None:
                raise ValueError("Respuesta XML inválida - Faltan elementos requeridos")
            
            codigo = codigo_elem.text
            mensaje = mensaje_elem.text
            
            result = {
                'codigo': codigo,
                'mensaje': mensaje,
                'data': None
            }
            
            logger.info(f"Respuesta DTE parseada - Código: {codigo}, Mensaje: {mensaje}")
            
            # Si código es 0422 (éxito), extraer datos del DTE
            if codigo == '0422':
                # El contenido viene escapado en xContenDE
                contenido_elem = body.find('ns2:xContenDE', XMLParser.NS)
                
                if contenido_elem is None:
                    logger.error("No se encontró xContenDE en respuesta exitosa")
                    raise ValueError("Respuesta XML inválida - Falta xContenDE")
                
                contenido_escapado = contenido_elem.text
                logger.debug(f"Contenido escapado: {contenido_escapado[:200]}...")
                
                # Usar múltiples pasadas de unescape para limpiar entidades HTML
                import re
                contenido_xml = html.unescape(contenido_escapado)
                contenido_xml = html.unescape(contenido_xml)  # Segunda pasada
                
                # Limpiar entidades problemáticas que quedan
                contenido_xml = re.sub(r'&amp;#13;\s*', '\n', contenido_xml)
                contenido_xml = re.sub(r'&amp;amp;', '&amp;', contenido_xml)
                contenido_xml = re.sub(r'&amp;#(\d+);', lambda m: chr(int(m.group(1))), contenido_xml)
                
                # Buscar el final de rDE completo para incluir gCamFuFD que está después de </DE>
                rde_start = contenido_xml.find('<rDE')
                signature_start = contenido_xml.find('<Signature')
                logger.info(f"rDE_start: {rde_start}, signature_start: {signature_start}")
                
                # Buscar también gCamFuFD en el contenido original
                gCamFuFD_in_original = contenido_xml.find('gCamFuFD')
                logger.info(f"gCamFuFD en contenido original: {gCamFuFD_in_original}")
                
                if rde_start != -1:
                    if signature_start != -1:
                        # Buscar gCamFuFD y dProtAut que están después de la firma
                        gCamFuFD_start = contenido_xml.find('<gCamFuFD>')
                        dProtAut_start = contenido_xml.find('<dProtAut>')
                        end_rde = contenido_xml.find('</rDE>')
                        
                        if gCamFuFD_start != -1 and gCamFuFD_start > signature_start:
                            # gCamFuFD está después de la firma, necesitamos incluirlo
                            if end_rde != -1:
                                # Tomar toda la sección rDE hasta el final natural
                                rde_content = contenido_xml[rde_start:end_rde + 6]
                                logger.info("Extraída sección rDE completa incluyendo gCamFuFD después de firma")
                            else:
                                # Reconstruir hasta el final del contenido
                                rde_content = contenido_xml[rde_start:]
                                if not rde_content.rstrip().endswith('</rDE>'):
                                    rde_content += '</rDE>'
                                logger.info("Reconstruida sección rDE completa con gCamFuFD")
                        else:
                            # gCamFuFD no está después de la firma o no existe
                            rde_content = contenido_xml[rde_start:signature_start]
                            if not rde_content.rstrip().endswith('</rDE>'):
                                rde_content += '</rDE>'
                            logger.info("Extraída sección rDE hasta firma (sin gCamFuFD posterior)")
                        
                        # Verificar si gCamFuFD está en el contenido final
                        gCamFuFD_in_extracted = rde_content.find('gCamFuFD')
                        logger.info(f"gCamFuFD en contenido final: {gCamFuFD_in_extracted}")
                        
                        contenido_xml = rde_content
                    else:
                        # Si no hay firma, buscar el cierre natural de rDE
                        end_rde = contenido_xml.find('</rDE>')
                        if end_rde != -1:
                            contenido_xml = contenido_xml[rde_start:end_rde + 6]  # +6 para incluir '</rDE>'
                            logger.info("Extraída sección rDE completa hasta cierre natural")
                        else:
                            # Si no hay cierre, tomar todo desde rDE
                            contenido_xml = contenido_xml[rde_start:] + '</rDE>'
                            logger.info("Reconstruida sección rDE sin cierre natural")
                
                logger.debug(f"Contenido limpio: {contenido_xml[:400]}...")
                
                # Log específico para buscar gCamFuFD en el contenido
                if 'gCamFuFD' in contenido_xml:
                    gCamFuFD_start = contenido_xml.find('<gCamFuFD>')
                    gCamFuFD_end = contenido_xml.find('</gCamFuFD>') + 11
                    if gCamFuFD_start != -1 and gCamFuFD_end != -1:
                        gCamFuFD_section = contenido_xml[gCamFuFD_start:gCamFuFD_end]
                        logger.info(f"SECCIÓN gCamFuFD ENCONTRADA: {gCamFuFD_section}")
                else:
                    logger.info("gCamFuFD NO ENCONTRADO en el contenido XML")
                
                # Parsear el XML del DTE usando xmltodict (más robusto)
                dte_data = XMLParser._parse_dte_content_robust(contenido_xml)
                result['data'] = dte_data
            
            return result
            
        except ET.ParseError as e:
            logger.error(f"Error de parseo XML DTE: {e}")
            logger.error(f"XML que causó el error: {xml_response}")
            raise Exception(f"XML mal formado: {str(e)}")
        except Exception as e:
            logger.error(f"Error parseando respuesta DTE: {e}")
            logger.error(f"XML completo: {xml_response}")
            raise
    
    @staticmethod
    def _parse_dte_content(xml_content: str) -> DTEData:
        """Parsear el contenido XML del DTE"""
        try:
            logger.debug("Iniciando parseo del contenido DTE")
            
            # Parsear el XML del DTE
            root = ET.fromstring(xml_content)
            
            # Namespace del DTE - usar prefijo vacío para el namespace por defecto
            ns = {'ns': 'http://ekuatia.set.gov.py/sifen/xsd'}
            
            # Buscar elementos sin namespace primero, luego con namespace
            de_element = root.find('.//DE') or root.find('.//ns:DE', ns)
            if de_element is None:
                raise ValueError("No se encontró el elemento DE")
                
            cdc = de_element.get('Id')
            logger.debug(f"CDC extraído: {cdc}")
            
            # Función auxiliar para buscar elementos con o sin namespace
            def find_element(path):
                return root.find(f'.//{path}') or root.find(f'.//ns:{path}', ns)
            
            def get_text_safe(element):
                return element.text if element is not None else ""
            
            # Buscar dProtAut (número de autorización) 
            prot_aut = find_element('dProtAut')
            numero_autorizacion = get_text_safe(prot_aut)
            
            # Datos generales
            fecha_emision = get_text_safe(find_element('dFeEmiDE'))
            
            # Timbrado
            tipo_doc = get_text_safe(find_element('dDesTiDE'))
            num_doc = get_text_safe(find_element('dNumDoc'))
            establecimiento = get_text_safe(find_element('dEst'))
            punto_exp = get_text_safe(find_element('dPunExp'))
            
            # Tipo de emisión y condición
            tipo_emision = get_text_safe(find_element('dDesTipEmi'))
            condicion_op = find_element('dDCondOpe')
            condicion_operacion = get_text_safe(condicion_op)
            
            # Emisor
            ruc_em = get_text_safe(find_element('dRucEm'))
            dv_emi = get_text_safe(find_element('dDVEmi'))
            ruc_completo = f"{ruc_em}-{dv_emi}" if ruc_em and dv_emi else ruc_em
            
            emisor = EmisorData(
                ruc=ruc_completo,
                nombre=get_text_safe(find_element('dNomEmi')),
                direccion=get_text_safe(find_element('dDirEmi')) or None,
                telefono=get_text_safe(find_element('dTelEmi')) or None,
                email=get_text_safe(find_element('dEmailE')) or None
            )
            
            # Receptor
            receptor_nombre = get_text_safe(find_element('dNomRec'))
            
            # Verificar si es con RUC o con otro tipo de ID
            ruc_rec = find_element('dRucRec')
            tipo_id_rec = find_element('dDTipIDRec')
            num_id_rec = find_element('dNumIDRec')
            dv_rec = find_element('dDVRec')
            
            receptor_ruc = None
            if ruc_rec is not None and dv_rec is not None:
                receptor_ruc = f"{ruc_rec.text}-{dv_rec.text}"
            
            receptor = ReceptorData(
                nombre=receptor_nombre,
                tipo_id=get_text_safe(tipo_id_rec) or None,
                numero_id=get_text_safe(num_id_rec) or None,
                ruc=receptor_ruc,
                direccion=get_text_safe(find_element('dDirRec')) or None,
                pais=get_text_safe(find_element('dDesPaisRe')) or None
            )
            
            # Totales - convertir a int de forma segura
            def get_int_safe(element, default=0):
                if element is not None and element.text:
                    try:
                        return int(float(element.text))
                    except (ValueError, TypeError):
                        return default
                return default
            
            totales = TotalesData(
                total_operacion=get_int_safe(find_element('dTotGralOpe')),
                total_iva=get_int_safe(find_element('dTotIVA')),
                total_iva_5=get_int_safe(find_element('dIVA5')),
                total_iva_10=get_int_safe(find_element('dIVA10')),
                total_exento=get_int_safe(find_element('dSubExe')),
                total_exonerado=get_int_safe(find_element('dSubExo')),
                moneda=get_text_safe(find_element('cMoneOpe')) or "PYG"
            )
            
            # Items
            items = []
            items_elements = root.findall('.//gCamItem') or root.findall('.//ns:gCamItem', ns)
            
            for item in items_elements:
                def find_in_item(path):
                    return item.find(path) or item.find(f'ns:{path}', ns)
                
                cod_int = find_in_item('dCodInt')
                desc = find_in_item('dDesProSer')
                cant = find_in_item('dCantProSer')
                precio = find_in_item('.//dPUniProSer') or find_in_item('dPUniProSer')
                total_item = find_in_item('.//dTotOpeItem') or find_in_item('dTotOpeItem')
                
                # IVA del item
                tasa_iva = find_in_item('.//dTasaIVA') or find_in_item('dTasaIVA')
                liq_iva = find_in_item('.//dLiqIVAItem') or find_in_item('dLiqIVAItem')
                
                # Funciones auxiliares para conversión segura
                def get_float_safe(elem, default=0.0):
                    if elem is not None and elem.text:
                        try:
                            return float(elem.text)
                        except (ValueError, TypeError):
                            return default
                    return default
                
                items.append(ItemData(
                    codigo=get_text_safe(cod_int),
                    descripcion=get_text_safe(desc),
                    cantidad=get_float_safe(cant),
                    precio_unitario=get_float_safe(precio),
                    total=get_int_safe(total_item),
                    iva_tipo=f"{tasa_iva.text}%" if tasa_iva is not None and tasa_iva.text else None,
                    iva_monto=get_int_safe(liq_iva)
                ))
            
            # URL del QR
            qr_url_elem = find_element('dCarQR')
            qr_url = get_text_safe(qr_url_elem) or None
            
            # Crear el objeto DTEData
            dte_data = DTEData(
                cdc=cdc,
                numero_autorizacion=numero_autorizacion,
                fecha_emision=fecha_emision,
                tipo_documento=tipo_doc,
                numero_documento=f"{establecimiento}-{punto_exp}-{num_doc}" if all([establecimiento, punto_exp, num_doc]) else "",
                establecimiento=establecimiento,
                punto_expedicion=punto_exp,
                tipo_emision=tipo_emision,
                condicion_operacion=condicion_operacion,
                emisor=emisor,
                receptor=receptor,
                totales=totales,
                items=items,
                qr_url=qr_url
            )
            
            logger.info(f"DTE parseado exitosamente: {cdc} - {emisor.nombre} -> {receptor.nombre}")
            logger.info(f"Items extraídos: {len(items)}, Total: {totales.total_operacion}")
            
            return dte_data
            
        except ET.ParseError as e:
            logger.error(f"Error de parseo XML contenido DTE: {e}")
            logger.error(f"XML contenido que causó el error: {xml_content[:500]}...")
            raise Exception(f"XML del DTE mal formado: {str(e)}")
        except Exception as e:
            logger.error(f"Error parseando contenido del DTE: {e}")
            logger.error(f"XML contenido: {xml_content[:500]}...")
            raise

    @staticmethod
    def _parse_dte_content_robust(xml_content: str) -> DTEData:
        """Parsear el contenido XML del DTE usando xmltodict (más robusto)"""
        try:
            logger.info(f"Iniciando parseo robusto del contenido DTE. XML recibido: {len(xml_content)} caracteres")
            logger.info(f"¿Contiene gCamFuFD?: {'gCamFuFD' in xml_content}")
            if 'gCamFuFD' in xml_content:
                start_pos = xml_content.find('gCamFuFD')
                logger.info(f"gCamFuFD encontrado en posición: {start_pos}")
            
            # Limpiar múltiples niveles de escape HTML
            import re
            contenido_xml = html.unescape(xml_content)
            contenido_xml = html.unescape(contenido_xml)  # Segunda pasada
            contenido_xml = html.unescape(contenido_xml)  # Tercera pasada para casos muy escapados
            
            # Limpiar entidades problemáticas específicas
            contenido_xml = re.sub(r'&amp;#13;\s*', '\n', contenido_xml)
            contenido_xml = re.sub(r'&amp;amp;', '&amp;', contenido_xml)
            contenido_xml = re.sub(r'&amp;#(\d+);', lambda m: chr(int(m.group(1))) if int(m.group(1)) < 127 else '', contenido_xml)
            
            # Limpiar caracteres de control problemáticos y caracteres no XML válidos
            contenido_xml = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', contenido_xml)
            
            # Limpiar entidades HTML restantes que puedan causar problemas
            contenido_xml = contenido_xml.replace('&nbsp;', ' ')
            contenido_xml = contenido_xml.replace('&copy;', '©')
            contenido_xml = contenido_xml.replace('&reg;', '®')
            
            # Asegurar que las entidades XML básicas estén correctas
            contenido_xml = contenido_xml.replace('&amp;amp;', '&amp;')
            contenido_xml = contenido_xml.replace('&lt;&lt;', '&lt;')
            contenido_xml = contenido_xml.replace('&gt;&gt;', '&gt;')
            
            logger.info(f"XML después de limpieza: {len(contenido_xml)} caracteres")
            
            # Mostrar las líneas problemáticas para debug
            lines = contenido_xml.split('\n')
            if len(lines) >= 41:
                logger.info(f"Línea 40: {repr(lines[39])}")
                logger.info(f"Línea 41: {repr(lines[40])}")
                if len(lines) >= 42:
                    logger.info(f"Línea 42: {repr(lines[41])}")
            
            logger.info(f"XML limpio preview: {contenido_xml[:500]}...")
            
            # Convertir XML a diccionario usando xmltodict
            try:
                xml_dict = xmltodict.parse(contenido_xml)
            except Exception as e:
                logger.error(f"Error con xmltodict, intentando fallback con ElementTree: {e}")
                # Fallback: usar el método original con ElementTree
                return XMLParser._parse_dte_content_fallback(contenido_xml)
            
            # Navegar al elemento rDE
            rde = xml_dict.get('rDE', {})
            de = rde.get('DE', {})
            
            # Extraer datos básicos
            cdc = de.get('@Id', '')
            logger.debug(f"CDC extraído: {cdc}")
            
            # Buscar dProtAut y dCodSeg
            numero_autorizacion = rde.get('dProtAut', '')
            codigo_seguridad = de.get('gOpeDE', {}).get('dCodSeg', '')
            
            # Datos de timbrado y documento
            gTimb = de.get('gTimb', {})
            tipo_doc = gTimb.get('dDesTiDE', '')
            num_doc = gTimb.get('dNumDoc', '')
            establecimiento = gTimb.get('dEst', '')
            punto_exp = gTimb.get('dPunExp', '')
            
            # Datos generales de operación
            gDatGralOpe = de.get('gDatGralOpe', {})
            fecha_emision = gDatGralOpe.get('dFeEmiDE', '')
            
            # Emisor
            gEmis = gDatGralOpe.get('gEmis', {})
            ruc_em = gEmis.get('dRucEm', '')
            dv_emi = gEmis.get('dDVEmi', '')
            ruc_completo = f"{ruc_em}-{dv_emi}" if ruc_em and dv_emi else ruc_em
            
            emisor = EmisorData(
                ruc=ruc_completo,
                nombre=gEmis.get('dNomEmi', ''),
                direccion=gEmis.get('dDirEmi', ''),
                telefono=gEmis.get('dTelEmi', ''),
                email=gEmis.get('dEmailE', '')
            )
            
            # Receptor
            gDatRec = gDatGralOpe.get('gDatRec', {})
            receptor_nombre = gDatRec.get('dNomRec', '')
            tipo_id = gDatRec.get('dDTipIDRec', '')
            numero_id = gDatRec.get('dNumIDRec', '')
            
            receptor = ReceptorData(
                nombre=receptor_nombre,
                tipo_id=tipo_id,
                numero_id=numero_id,
                ruc=None,  # Por ahora
                direccion=gDatRec.get('dDirRec', ''),
                pais=gDatRec.get('dDesPaisRe', '')
            )
            
            # Totales
            gTotSub = de.get('gTotSub', {})
            
            def safe_int(value, default=0):
                try:
                    return int(float(str(value))) if value else default
                except (ValueError, TypeError):
                    return default
            
            totales = TotalesData(
                total_operacion=safe_int(gTotSub.get('dTotGralOpe')),
                total_iva=safe_int(gTotSub.get('dTotIVA')),
                total_iva_5=safe_int(gTotSub.get('dIVA5')),
                total_iva_10=safe_int(gTotSub.get('dIVA10')),
                total_exento=safe_int(gTotSub.get('dSubExe')),
                total_exonerado=safe_int(gTotSub.get('dSubExo')),
                moneda=gDatGralOpe.get('gOpeCom', {}).get('cMoneOpe', 'PYG')
            )
            
            # Items
            items = []
            gDtipDE = de.get('gDtipDE', {})
            gCamItems = gDtipDE.get('gCamItem', [])
            
            # Si gCamItem es un solo item (dict), convertirlo a lista
            if isinstance(gCamItems, dict):
                gCamItems = [gCamItems]
            
            for item_data in gCamItems:
                def safe_float(value, default=0.0):
                    try:
                        return float(str(value)) if value else default
                    except (ValueError, TypeError):
                        return default
                
                gValorItem = item_data.get('gValorItem', {})
                gCamIVA = item_data.get('gCamIVA', {})
                
                items.append(ItemData(
                    codigo=item_data.get('dCodInt', ''),
                    descripcion=item_data.get('dDesProSer', ''),
                    cantidad=safe_float(item_data.get('dCantProSer')),
                    precio_unitario=safe_float(gValorItem.get('dPUniProSer')),
                    total=safe_int(gValorItem.get('dTotOpeItem')),
                    iva_tipo=f"{gCamIVA.get('dTasaIVA', '')}%" if gCamIVA.get('dTasaIVA') else None,
                    iva_monto=safe_int(gCamIVA.get('dLiqIVAItem'))
                ))
            
            # URL del QR - buscar en gCamFuFD que está fuera del elemento DE
            qr_url = None
            
            logger.info("=== INICIANDO BÚSQUEDA DE QR URL ===")
            logger.info(f"Estructura rDE keys: {list(rde.keys())}")
            
            # Primero buscar en gCamFuFD dentro de rDE (fuera de DE)
            gCamFuFD = rde.get('gCamFuFD', {})
            logger.info(f"gCamFuFD encontrado: {bool(gCamFuFD)}")
            if gCamFuFD:
                logger.info(f"gCamFuFD keys: {list(gCamFuFD.keys())}")
                qr_url_raw = gCamFuFD.get('dCarQR', '')
                logger.info(f"dCarQR raw: '{qr_url_raw[:200]}...' (len={len(qr_url_raw)})")
                if qr_url_raw:
                    # Limpiar entidades HTML del QR
                    qr_url = html.unescape(qr_url_raw)
                    qr_url = qr_url.replace('&amp;', '&')
                    logger.info(f"QR URL extraída de gCamFuFD: {qr_url[:100]}...")
            
            # Si no se encuentra, buscar en otras ubicaciones posibles
            if not qr_url:
                logger.info("QR no encontrado en gCamFuFD, buscando recursivamente...")
                # Buscar directamente en el diccionario completo por si está en otro lugar
                def find_qr_recursive(data, key='dCarQR'):
                    if isinstance(data, dict):
                        if key in data:
                            return data[key]
                        for k, v in data.items():
                            result = find_qr_recursive(v, key)
                            if result:
                                return result
                    elif isinstance(data, list):
                        for item in data:
                            result = find_qr_recursive(item, key)
                            if result:
                                return result
                    return None
                
                qr_url_raw = find_qr_recursive(xml_dict)
                logger.info(f"Búsqueda recursiva resultado: '{qr_url_raw[:100] if qr_url_raw else 'None'}...'")
                if qr_url_raw:
                    qr_url = html.unescape(qr_url_raw)
                    qr_url = qr_url.replace('&amp;', '&')
                    logger.info(f"QR URL encontrada recursivamente: {qr_url[:100]}...")
            
            logger.info(f"=== QR URL FINAL: {qr_url[:100] if qr_url else 'NULL'} ===")
            
            # Crear objeto DTEData
            dte_data = DTEData(
                cdc=cdc,
                numero_autorizacion=numero_autorizacion,
                codigo_seguridad=codigo_seguridad,  # Nuevo campo
                fecha_emision=fecha_emision,
                tipo_documento=tipo_doc,
                numero_documento=f"{establecimiento}-{punto_exp}-{num_doc}" if all([establecimiento, punto_exp, num_doc]) else "",
                establecimiento=establecimiento,
                punto_expedicion=punto_exp,
                tipo_emision=de.get('gOpeDE', {}).get('dDesTipEmi', ''),
                condicion_operacion=gDtipDE.get('gCamCond', {}).get('dDCondOpe', ''),
                emisor=emisor,
                receptor=receptor,
                totales=totales,
                items=items,
                qr_url=qr_url
            )
            
            logger.info(f"DTE parseado exitosamente: {cdc} - {emisor.nombre} -> {receptor.nombre}")
            logger.info(f"Items: {len(items)}, Total: {totales.total_operacion}, QR: {'Sí' if qr_url else 'No'}")
            
            return dte_data
            
        except Exception as e:
            logger.error(f"Error en parseo robusto del DTE: {e}")
            logger.error(f"XML contenido: {xml_content[:500]}...")
            raise Exception(f"Error procesando DTE: {str(e)}")

    @staticmethod
    def _parse_dte_content_fallback(xml_content: str) -> DTEData:
        """Método de fallback usando ElementTree cuando xmltodict falla"""
        try:
            logger.info("Usando método de fallback con ElementTree")
            
            # Importar modelos necesarios
            from models.schemas import DTEData, EmisorData, ReceptorData, TotalesData, ItemData
            
            # Usar ElementTree con manejo de entidades más flexible
            import xml.etree.ElementTree as ET
            
            # Limpiezas adicionales específicas para ElementTree
            xml_content_clean = xml_content
            
            # Buscar manualmente el QR en el XML como string
            qr_url = None
            if '<dCarQR>' in xml_content_clean:
                start_qr = xml_content_clean.find('<dCarQR>') + len('<dCarQR>')
                end_qr = xml_content_clean.find('</dCarQR>')
                if start_qr != -1 and end_qr != -1 and end_qr > start_qr:
                    qr_url_raw = xml_content_clean[start_qr:end_qr]
                    qr_url = html.unescape(qr_url_raw)
                    qr_url = qr_url.replace('&amp;', '&')
                    logger.info(f"QR URL extraído manualmente: {qr_url[:100]}...")
            
            # Parsear con ElementTree para obtener el resto de los datos
            try:
                root = ET.fromstring(xml_content_clean)
            except ET.ParseError:
                # Si falla, remover la sección problemática y continuar
                logger.warning("ElementTree falló, extrayendo datos básicos...")
                
                # Extraer todos los datos usando regex como último recurso
                import re
                
                # Datos básicos del documento
                cdc_match = re.search(r'Id="([^"]*)"', xml_content_clean)
                cdc = cdc_match.group(1) if cdc_match else ""
                
                auth_match = re.search(r'<dProtAut>([^<]*)</dProtAut>', xml_content_clean)
                numero_autorizacion = auth_match.group(1) if auth_match else ""
                
                # Código de seguridad
                cod_seg_match = re.search(r'<dCodSeg>([^<]*)</dCodSeg>', xml_content_clean)
                codigo_seguridad = cod_seg_match.group(1) if cod_seg_match else ""
                
                # Fecha de emisión
                fecha_match = re.search(r'<dFecFirma>([^<]*)</dFecFirma>', xml_content_clean)
                fecha_emision = fecha_match.group(1) if fecha_match else ""
                
                # Tipo de documento
                tipo_doc_match = re.search(r'<dDesTiDE>([^<]*)</dDesTiDE>', xml_content_clean)
                tipo_documento = tipo_doc_match.group(1) if tipo_doc_match else ""
                
                # Número de documento
                num_doc_match = re.search(r'<dNumDoc>([^<]*)</dNumDoc>', xml_content_clean)
                numero_documento = num_doc_match.group(1) if num_doc_match else ""
                
                # Establecimiento y punto de expedición
                est_match = re.search(r'<dEst>([^<]*)</dEst>', xml_content_clean)
                establecimiento = est_match.group(1) if est_match else ""
                
                pto_exp_match = re.search(r'<dPunExp>([^<]*)</dPunExp>', xml_content_clean)
                punto_expedicion = pto_exp_match.group(1) if pto_exp_match else ""
                
                # Datos del emisor - probando diferentes variaciones de tags
                emi_ruc_match = re.search(r'<dRucEm>([^<]*)</dRucEm>', xml_content_clean)
                if not emi_ruc_match:
                    emi_ruc_match = re.search(r'<dRUCEmi>([^<]*)</dRUCEmi>', xml_content_clean)
                emi_ruc = emi_ruc_match.group(1) if emi_ruc_match else ""
                
                # Dígito verificador del emisor
                emi_dv_match = re.search(r'<dDVId>([^<]*)</dDVId>', xml_content_clean)
                if not emi_dv_match:
                    emi_dv_match = re.search(r'<dDVEmi>([^<]*)</dDVEmi>', xml_content_clean)
                emi_dv = emi_dv_match.group(1) if emi_dv_match else ""
                
                emi_nombre_match = re.search(r'<dRazEmi>([^<]*)</dRazEmi>', xml_content_clean)
                if not emi_nombre_match:
                    emi_nombre_match = re.search(r'<dNomEmi>([^<]*)</dNomEmi>', xml_content_clean)
                if not emi_nombre_match:
                    emi_nombre_match = re.search(r'<dRazSoc>([^<]*)</dRazSoc>', xml_content_clean)
                emi_nombre = emi_nombre_match.group(1) if emi_nombre_match else "Emisor no disponible"
                
                emi_dir_match = re.search(r'<dDirEmi>([^<]*)</dDirEmi>', xml_content_clean)
                emi_direccion = emi_dir_match.group(1) if emi_dir_match else ""
                
                emi_tel_match = re.search(r'<dTelEmi>([^<]*)</dTelEmi>', xml_content_clean)
                emi_telefono = emi_tel_match.group(1) if emi_tel_match else ""
                
                emi_email_match = re.search(r'<dEmailE>([^<]*)</dEmailE>', xml_content_clean)
                emi_email = emi_email_match.group(1) if emi_email_match else ""
                
                # Datos del receptor
                rec_nombre_match = re.search(r'<dNomRec>([^<]*)</dNomRec>', xml_content_clean)
                rec_nombre = rec_nombre_match.group(1) if rec_nombre_match else "Receptor no disponible"
                
                # Buscar RUC del receptor
                rec_ruc_match = re.search(r'<dRucRec>([^<]*)</dRucRec>', xml_content_clean)
                rec_ruc = rec_ruc_match.group(1) if rec_ruc_match else ""
                
                # Dígito verificador del receptor
                rec_dv_match = re.search(r'<dDVRec>([^<]*)</dDVRec>', xml_content_clean)
                rec_dv = rec_dv_match.group(1) if rec_dv_match else ""
                
                # Si no tiene RUC, buscar cédula de identidad
                rec_ci = ""
                if not rec_ruc:
                    rec_ci_match = re.search(r'<dNumIDRec>([^<]*)</dNumIDRec>', xml_content_clean)
                    if not rec_ci_match:
                        rec_ci_match = re.search(r'<dCedRec>([^<]*)</dCedRec>', xml_content_clean)
                    rec_ci = rec_ci_match.group(1) if rec_ci_match else ""
                
                # Determinar tipo de documento del receptor
                rec_tipo_id = "RUC" if rec_ruc else "CI"
                rec_numero_id = rec_ruc if rec_ruc else rec_ci
                
                rec_dir_match = re.search(r'<dDirRec>([^<]*)</dDirRec>', xml_content_clean)
                rec_direccion = rec_dir_match.group(1) if rec_dir_match else ""
                
                # Totales - probando diferentes variaciones
                total_op_match = re.search(r'<dTotOpe>([^<]*)</dTotOpe>', xml_content_clean)
                if not total_op_match:
                    total_op_match = re.search(r'<dTotGralOpe>([^<]*)</dTotGralOpe>', xml_content_clean)
                total_operacion = float(total_op_match.group(1)) if total_op_match and total_op_match.group(1) else 0
                
                total_iva_match = re.search(r'<dTotIVA>([^<]*)</dTotIVA>', xml_content_clean)
                if not total_iva_match:
                    total_iva_match = re.search(r'<dLiqTotIVA>([^<]*)</dLiqTotIVA>', xml_content_clean)
                total_iva = float(total_iva_match.group(1)) if total_iva_match and total_iva_match.group(1) else 0
                
                # Si no se encontraron totales en XML, intentar extraer del QR URL como backup
                if total_operacion == 0 and qr_url:
                    qr_total_match = re.search(r'dTotGralOpe=(\d+)', qr_url)
                    if qr_total_match:
                        total_operacion = float(qr_total_match.group(1))
                        
                if total_iva == 0 and qr_url:
                    qr_iva_match = re.search(r'dTotIVA=(\d+)', qr_url)
                    if qr_iva_match:
                        total_iva = float(qr_iva_match.group(1))
                
                # Moneda (por defecto PYG para Paraguay)
                moneda_match = re.search(r'<cMoneOpe>([^<]*)</cMoneOpe>', xml_content_clean)
                moneda = moneda_match.group(1) if moneda_match else "PYG"
                
                # Extraer ítems/productos
                items = []
                # Buscar todas las secciones de ítems en el XML
                item_pattern = r'<gCamItem>.*?</gCamItem>'
                item_matches = re.findall(item_pattern, xml_content_clean, re.DOTALL)
                
                logger.info(f"Buscando ítems con patrón gCamItem - Encontrados: {len(item_matches)}")
                
                # Si no encuentra con gCamItem, probar con otros patrones
                if len(item_matches) == 0:
                    item_pattern2 = r'<gCamIteGS07>.*?</gCamIteGS07>'
                    item_matches = re.findall(item_pattern2, xml_content_clean, re.DOTALL)
                    logger.info(f"Buscando ítems con patrón gCamIteGS07 - Encontrados: {len(item_matches)}")
                
                if len(item_matches) == 0:
                    # Buscar cualquier sección que contenga descripciones de productos
                    desc_matches = re.findall(r'<dDesProSer>([^<]*)</dDesProSer>', xml_content_clean)
                    logger.info(f"Descripciones de productos encontradas: {len(desc_matches)}: {desc_matches[:3] if desc_matches else 'Ninguna'}")
                
                for i, item_match in enumerate(item_matches):
                    try:
                        # Extraer datos de cada ítem
                        codigo_match = re.search(r'<dCodInt>([^<]*)</dCodInt>', item_match)
                        codigo = codigo_match.group(1) if codigo_match else ""
                        
                        desc_match = re.search(r'<dDesProSer>([^<]*)</dDesProSer>', item_match)
                        descripcion = desc_match.group(1) if desc_match else ""
                        
                        cant_match = re.search(r'<dCantProSer>([^<]*)</dCantProSer>', item_match)
                        cantidad = float(cant_match.group(1)) if cant_match and cant_match.group(1) else 0
                        
                        precio_match = re.search(r'<dPUniProSer>([^<]*)</dPUniProSer>', item_match)
                        precio_unitario = float(precio_match.group(1)) if precio_match and precio_match.group(1) else 0
                        
                        total_match = re.search(r'<dTotBruOpeItem>([^<]*)</dTotBruOpeItem>', item_match)
                        if not total_match:
                            total_match = re.search(r'<dTotOpeItem>([^<]*)</dTotOpeItem>', item_match)
                        total_item = int(float(total_match.group(1))) if total_match and total_match.group(1) else 0
                        
                        # IVA del ítem
                        iva_tipo_match = re.search(r'<dTasaIVA>([^<]*)</dTasaIVA>', item_match)
                        iva_tipo = f"{iva_tipo_match.group(1)}%" if iva_tipo_match else None
                        
                        iva_monto_match = re.search(r'<dBasGravIVA>([^<]*)</dBasGravIVA>', item_match)
                        iva_monto = int(float(iva_monto_match.group(1))) if iva_monto_match and iva_monto_match.group(1) else None
                        
                        if descripcion:  # Solo agregar si tiene descripción
                            item = ItemData(
                                codigo=codigo,
                                descripcion=descripcion,
                                cantidad=cantidad,
                                precio_unitario=precio_unitario,
                                total=total_item,
                                iva_tipo=iva_tipo,
                                iva_monto=iva_monto
                            )
                            items.append(item)
                            
                    except Exception as e:
                        logger.warning(f"Error extrayendo ítem: {e}")
                        continue
                
                logger.info(f"Datos extraídos con regex - CDC: {cdc}, Emisor RUC: {emi_ruc}-{emi_dv}, Emisor: {emi_nombre}, Receptor {rec_tipo_id}: {rec_numero_id}{'-' + rec_dv if rec_dv else ''}, Receptor: {rec_nombre}, Total: {total_operacion}, IVA: {total_iva}, Items: {len(items)}")
                
                # Crear un DTE completo con todos los datos extraídos
                return DTEData(
                    cdc=cdc,
                    numero_autorizacion=numero_autorizacion,
                    codigo_seguridad=codigo_seguridad,
                    fecha_emision=fecha_emision,
                    tipo_documento=tipo_documento,
                    numero_documento=numero_documento,
                    establecimiento=establecimiento,
                    punto_expedicion=punto_expedicion,
                    tipo_emision="Normal",  # Por defecto
                    condicion_operacion="Contado",  # Por defecto
                    emisor=EmisorData(
                        ruc=emi_ruc,
                        dv=emi_dv,
                        nombre=emi_nombre,
                        direccion=emi_direccion,
                        telefono=emi_telefono,
                        email=emi_email
                    ),
                    receptor=ReceptorData(
                        nombre=rec_nombre,
                        tipo_id=rec_tipo_id,
                        numero_id=rec_numero_id,
                        ruc=rec_ruc if rec_ruc else None,
                        dv=rec_dv if rec_dv else None,
                        direccion=rec_direccion,
                        pais="Paraguay"
                    ),
                    totales=TotalesData(
                        total_operacion=total_operacion,
                        total_iva=total_iva,
                        moneda=moneda
                    ),
                    items=items,
                    qr_url=qr_url
                )
            
            # Si ElementTree funciona, extraer datos normalmente pero con el QR manual
            logger.info("ElementTree exitoso, extrayendo datos completos")
            
            # Crear un DTEData básico por ahora con el QR extraído
            return DTEData(
                cdc="",
                numero_autorizacion="",
                codigo_seguridad="",
                fecha_emision="",
                tipo_documento="",
                numero_documento="",
                establecimiento="",
                punto_expedicion="",
                tipo_emision="",
                condicion_operacion="",
                emisor=EmisorData(ruc="", nombre="Procesando...", direccion="", telefono="", email=""),
                receptor=ReceptorData(nombre="Procesando...", tipo_id="", numero_id="", ruc="", direccion="", pais=""),
                totales=TotalesData(total_operacion=0, total_iva=0, moneda="PYG"),
                items=[],
                qr_url=qr_url
            )
            
        except Exception as e:
            logger.error(f"Error en método de fallback: {e}")
            raise Exception(f"Error en fallback: {str(e)}")


# Instancia global del parser
xml_parser = XMLParser()
