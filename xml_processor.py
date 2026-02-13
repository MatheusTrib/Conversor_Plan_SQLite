"""
Módulo de Processamento de XML - NFe e CTe
Baseado em scripts Power Query (M) fornecidos
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from typing import Dict, List, Tuple, Optional
import re

class XMLProcessor:
    """Processador de arquivos XML de NFe e CTe"""
    
    # Namespaces comuns em NFe/CTe
    NAMESPACES = {
        'nfe': 'http://www.portalfiscal.inf.br/nfe',
        'cte': 'http://www.portalfiscal.inf.br/cte',
        'ds': 'http://www.w3.org/2000/09/xmldsig#'
    }
    
    def __init__(self):
        self.nfe_data = []
        self.cte_data = []
    
    def detect_xml_type(self, xml_path: Path) -> Optional[str]:
        """Detecta se é NFe, CTe ou outro tipo de XML"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Remove namespace para facilitar detecção
            tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
            
            if 'nfeProc' in tag or 'NFe' in tag:
                return 'NFe'
            elif 'cteProc' in tag or 'CTe' in tag:
                return 'CTe'
            else:
                return None
        except:
            return None
    
    def get_text(self, element, path: str, namespaces: dict = None) -> Optional[str]:
        """Obtém texto de um elemento XML com segurança"""
        if element is None:
            return None
        
        try:
            found = element.find(path, namespaces or {})
            return found.text if found is not None else None
        except:
            return None
    
    def process_nfe_file(self, xml_path: Path) -> List[Dict]:
        """
        Processa arquivo NFe baseado no script M fornecido
        Retorna lista de dicionários (um por item da nota)
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Registra namespaces
            ns = self.NAMESPACES
            
            # Busca NFe (pode estar em nfeProc ou diretamente)
            nfe_elem = root.find('.//nfe:NFe', ns) or root.find('.//NFe')
            if nfe_elem is None:
                return []
            
            inf_nfe = nfe_elem.find('.//nfe:infNFe', ns) or nfe_elem.find('.//infNFe')
            if inf_nfe is None:
                return []
            
            # Extrai chave NFe
            chave_nfe = inf_nfe.get('Id', '').replace('NFe', '')
            
            # IDE - Identificação
            ide = inf_nfe.find('.//nfe:ide', ns) or inf_nfe.find('.//ide')
            nat_op = self.get_text(ide, './/nfe:natOp', ns) or self.get_text(ide, './/natOp')
            serie = self.get_text(ide, './/nfe:serie', ns) or self.get_text(ide, './/serie')
            num_nf = self.get_text(ide, './/nfe:nNF', ns) or self.get_text(ide, './/nNF')
            dh_emi = self.get_text(ide, './/nfe:dhEmi', ns) or self.get_text(ide, './/dhEmi')
            tp_nf = self.get_text(ide, './/nfe:tpNF', ns) or self.get_text(ide, './/tpNF')
            id_dest = self.get_text(ide, './/nfe:idDest', ns) or self.get_text(ide, './/idDest')
            
            # Converte tipo de NF
            tp_nf_desc = 'Saída' if tp_nf == '1' else 'Entrada' if tp_nf == '0' else tp_nf
            
            # Converte local operação
            local_op_map = {'1': 'Interna', '2': 'Interestadual', '3': 'Exterior'}
            local_op = local_op_map.get(id_dest, id_dest)
            
            # NFe referenciada
            nf_ref_elem = ide.find('.//nfe:NFref/nfe:refNFe', ns) or ide.find('.//NFref/refNFe')
            nf_ref = nf_ref_elem.text if nf_ref_elem is not None else None
            
            # EMIT - Emitente
            emit = inf_nfe.find('.//nfe:emit', ns) or inf_nfe.find('.//emit')
            cnpj_emit = self.get_text(emit, './/nfe:CNPJ', ns) or self.get_text(emit, './/CNPJ')
            nome_emit = self.get_text(emit, './/nfe:xNome', ns) or self.get_text(emit, './/xNome')
            ie_emit = self.get_text(emit, './/nfe:IE', ns) or self.get_text(emit, './/IE')
            im_emit = self.get_text(emit, './/nfe:IM', ns) or self.get_text(emit, './/IM')
            iest_emit = self.get_text(emit, './/nfe:IEST', ns) or self.get_text(emit, './/IEST')
            crt_emit = self.get_text(emit, './/nfe:CRT', ns) or self.get_text(emit, './/CRT')
            
            # UF Emitente
            uf_emit = self.get_text(emit, './/nfe:enderEmit/nfe:UF', ns) or self.get_text(emit, './/enderEmit/UF')
            
            # Regime tributário
            regime_map = {'1': 'Simples Nacional', '3': 'Regime Normal'}
            regime_trib = regime_map.get(crt_emit, crt_emit)
            
            # DEST - Destinatário
            dest = inf_nfe.find('.//nfe:dest', ns) or inf_nfe.find('.//dest')
            cnpj_dest = self.get_text(dest, './/nfe:CNPJ', ns) or self.get_text(dest, './/CNPJ')
            nome_dest = self.get_text(dest, './/nfe:xNome', ns) or self.get_text(dest, './/xNome')
            ie_dest = self.get_text(dest, './/nfe:IE', ns) or self.get_text(dest, './/IE')
            uf_dest = self.get_text(dest, './/nfe:enderDest/nfe:UF', ns) or self.get_text(dest, './/enderDest/UF')
            
            # TRANSP - Transporte
            transp = inf_nfe.find('.//nfe:transp', ns) or inf_nfe.find('.//transp')
            mod_frete = self.get_text(transp, './/nfe:modFrete', ns) or self.get_text(transp, './/modFrete')
            
            # Modalidade frete
            frete_map = {
                '0': 'Remetente', '1': 'Destinatário', '2': 'Terceiros',
                '3': 'Transporte próprio remetente', '4': 'Transporte próprio Destinatário',
                '9': 'Sem Transporte'
            }
            mod_frete_desc = frete_map.get(mod_frete, mod_frete)
            
            # Processa DATA - converte de ISO
            data_emissao = None
            if dh_emi:
                data_emissao = dh_emi.split('T')[0] if 'T' in dh_emi else dh_emi
            
            # DET - Detalhes (itens)
            itens = []
            det_list = inf_nfe.findall('.//nfe:det', ns) or inf_nfe.findall('.//det')
            
            for det in det_list:
                n_item = det.get('nItem', '0')
                
                # PROD - Produto
                prod = det.find('.//nfe:prod', ns) or det.find('.//prod')
                cod_prod = self.get_text(prod, './/nfe:cProd', ns) or self.get_text(prod, './/cProd')
                desc_prod = self.get_text(prod, './/nfe:xProd', ns) or self.get_text(prod, './/xProd')
                ncm = self.get_text(prod, './/nfe:NCM', ns) or self.get_text(prod, './/NCM')
                cfop = self.get_text(prod, './/nfe:CFOP', ns) or self.get_text(prod, './/CFOP')
                un_com = self.get_text(prod, './/nfe:uCom', ns) or self.get_text(prod, './/uCom')
                qtd_com = self.get_text(prod, './/nfe:qCom', ns) or self.get_text(prod, './/qCom')
                vlr_un = self.get_text(prod, './/nfe:vUnCom', ns) or self.get_text(prod, './/vUnCom')
                vlr_prod = self.get_text(prod, './/vProd', ns) or self.get_text(prod, './/vProd')
                cest = self.get_text(prod, './/nfe:CEST', ns) or self.get_text(prod, './/CEST')
                
                # IMPOSTO
                imposto = det.find('.//nfe:imposto', ns) or det.find('.//imposto')
                
                # ICMS
                icms_data = self._extract_icms(imposto, ns)
                
                # IPI
                ipi_data = self._extract_ipi(imposto, ns)
                
                # PIS
                pis_data = self._extract_pis(imposto, ns)
                
                # COFINS
                cofins_data = self._extract_cofins(imposto, ns)
                
                # Monta registro do item
                item_data = {
                    # Identificação da nota
                    'Natureza da Operação': nat_op,
                    'Série': serie,
                    'Nº NF': num_nf,
                    'Data': data_emissao,
                    'Tipo de NF': tp_nf_desc,
                    'Local Operação': local_op,
                    'NF Ref.': nf_ref,
                    
                    # Emitente
                    'CNPJ Emitente': cnpj_emit,
                    'Emitente': nome_emit,
                    'UF Emitente': uf_emit,
                    'IE Emitente': ie_emit,
                    'Insc. Municipal Emitente': im_emit,
                    'IE Substituta Emitente': iest_emit,
                    'Regime Tributario': regime_trib,
                    
                    # Destinatário
                    'CNPJ Destinatário': cnpj_dest,
                    'Nome destinatário': nome_dest,
                    'UF Destinatário': uf_dest,
                    'IE destinatário': ie_dest,
                    
                    # Item
                    'Nº Item': str(int(n_item)).zfill(2),
                    'Código produto': cod_prod,
                    'Descrição produto': desc_prod,
                    'NCM': ncm,
                    'CFOP': cfop,
                    'Unid. medida': un_com,
                    'Quantidade': qtd_com,
                    'Vlr Unitário': vlr_un,
                    'Vlr Produto': vlr_prod,
                    'CEST': cest,
                    
                    # ICMS
                    **icms_data,
                    
                    # IPI
                    **ipi_data,
                    
                    # PIS
                    **pis_data,
                    
                    # COFINS
                    **cofins_data,
                    
                    # Transporte
                    'Modalidade Frete': mod_frete_desc,
                    
                    # Chave
                    'Chave NFe': chave_nfe
                }
                
                itens.append(item_data)
            
            return itens
            
        except Exception as e:
            print(f"Erro ao processar NFe {xml_path}: {str(e)}")
            return []
    
    def _extract_icms(self, imposto, ns) -> Dict:
        """Extrai dados de ICMS (todos os CSTs)"""
        icms_elem = imposto.find('.//nfe:ICMS', ns) or imposto.find('.//ICMS')
        if icms_elem is None:
            return {}
        
        # Tenta todos os CSTs possíveis
        cst_tags = ['ICMS00', 'ICMS10', 'ICMS20', 'ICMS30', 'ICMS40', 
                    'ICMS50', 'ICMS51', 'ICMS60', 'ICMS61', 'ICMS70', 'ICMS90']
        
        origem = cst_icms = red_bc = bc_icms = aliq_icms = vlr_icms = None
        mva_icms = bc_icms_st = aliq_st = vlr_icms_st = None
        parte_dif = vlr_dif = bc_mono = aliq_adrem = vlr_mono = None
        bc_ret = aliq_ret = vlr_ret = None
        
        for cst_tag in cst_tags:
            cst_elem = icms_elem.find(f'.//nfe:{cst_tag}', ns) or icms_elem.find(f'.//{cst_tag}')
            if cst_elem is not None:
                origem = origem or self.get_text(cst_elem, './/nfe:orig', ns) or self.get_text(cst_elem, './/orig')
                cst_icms = cst_icms or self.get_text(cst_elem, './/nfe:CST', ns) or self.get_text(cst_elem, './/CST')
                
                # Campos comuns
                red_bc = red_bc or self.get_text(cst_elem, './/nfe:pRedBC', ns) or self.get_text(cst_elem, './/pRedBC')
                bc_icms = bc_icms or self.get_text(cst_elem, './/nfe:vBC', ns) or self.get_text(cst_elem, './/vBC')
                aliq_icms = aliq_icms or self.get_text(cst_elem, './/nfe:pICMS', ns) or self.get_text(cst_elem, './/pICMS')
                vlr_icms = vlr_icms or self.get_text(cst_elem, './/nfe:vICMS', ns) or self.get_text(cst_elem, './/vICMS')
                
                # ST
                mva_icms = mva_icms or self.get_text(cst_elem, './/nfe:pMVAST', ns) or self.get_text(cst_elem, './/pMVAST')
                bc_icms_st = bc_icms_st or self.get_text(cst_elem, './/nfe:vBCST', ns) or self.get_text(cst_elem, './/vBCST')
                aliq_st = aliq_st or self.get_text(cst_elem, './/nfe:pICMSST', ns) or self.get_text(cst_elem, './/pICMSST')
                vlr_icms_st = vlr_icms_st or self.get_text(cst_elem, './/nfe:vICMSST', ns) or self.get_text(cst_elem, './/vICMSST')
                
                # Diferimento (ICMS51)
                parte_dif = parte_dif or self.get_text(cst_elem, './/nfe:pDif', ns) or self.get_text(cst_elem, './/pDif')
                vlr_dif = vlr_dif or self.get_text(cst_elem, './/nfe:vICMSDif', ns) or self.get_text(cst_elem, './/vICMSDif')
                
                # Monofásico (ICMS61)
                bc_mono = bc_mono or self.get_text(cst_elem, './/nfe:qBCMonoRet', ns) or self.get_text(cst_elem, './/qBCMonoRet')
                aliq_adrem = aliq_adrem or self.get_text(cst_elem, './/nfe:adRemICMSRet', ns) or self.get_text(cst_elem, './/adRemICMSRet')
                vlr_mono = vlr_mono or self.get_text(cst_elem, './/nfe:vICMSMonoRet', ns) or self.get_text(cst_elem, './/vICMSMonoRet')
                
                # Retido (ICMS60)
                bc_ret = bc_ret or self.get_text(cst_elem, './/nfe:vBCSTRet', ns) or self.get_text(cst_elem, './/vBCSTRet')
                aliq_ret = aliq_ret or self.get_text(cst_elem, './/nfe:pST', ns) or self.get_text(cst_elem, './/pST')
                vlr_ret = vlr_ret or self.get_text(cst_elem, './/nfe:vICMSSTRet', ns) or self.get_text(cst_elem, './/vICMSSTRet')
        
        return {
            'Origem': origem,
            'CST ICMS': cst_icms,
            'Red. BC ICMS': red_bc,
            'BC ICMS': bc_icms,
            'Alíq. ICMS': aliq_icms,
            'Vlr ICMS': vlr_icms,
            'MVA ICMS': mva_icms,
            'BC ICMS ST': bc_icms_st,
            'Alíq. ST ICMS': aliq_st,
            'Vlr ICMS ST': vlr_icms_st,
            'Parte Diferida ICMS': parte_dif,
            'Vlr ICMS Dif.': vlr_dif,
            'BC ICMS Monofásico': bc_mono,
            'Alíq. AdRem': aliq_adrem,
            'Vlr ICMS Monofásico': vlr_mono,
            'BC ICMS Retido': bc_ret,
            'Alíq. ICMS Retido': aliq_ret,
            'Vlr ICMS Retido': vlr_ret
        }
    
    def _extract_ipi(self, imposto, ns) -> Dict:
        """Extrai dados de IPI"""
        ipi_elem = imposto.find('.//nfe:IPI', ns) or imposto.find('.//IPI')
        if ipi_elem is None:
            return {}
        
        # IPITrib ou IPINT
        ipi_trib = ipi_elem.find('.//nfe:IPITrib', ns) or ipi_elem.find('.//IPITrib')
        ipi_nt = ipi_elem.find('.//nfe:IPINT', ns) or ipi_elem.find('.//IPINT')
        
        cst = bc = aliq = vlr = None
        
        if ipi_trib is not None:
            cst = self.get_text(ipi_trib, './/nfe:CST', ns) or self.get_text(ipi_trib, './/CST')
            bc = self.get_text(ipi_trib, './/nfe:vBC', ns) or self.get_text(ipi_trib, './/vBC')
            aliq = self.get_text(ipi_trib, './/nfe:pIPI', ns) or self.get_text(ipi_trib, './/pIPI')
            vlr = self.get_text(ipi_trib, './/nfe:vIPI', ns) or self.get_text(ipi_trib, './/vIPI')
        elif ipi_nt is not None:
            cst = self.get_text(ipi_nt, './/nfe:CST', ns) or self.get_text(ipi_nt, './/CST')
        
        return {
            'CST IPI': cst,
            'BC IPI': bc,
            'Aliq. IPI': aliq,
            'Vlr IPI': vlr
        }
    
    def _extract_pis(self, imposto, ns) -> Dict:
        """Extrai dados de PIS"""
        pis_elem = imposto.find('.//nfe:PIS', ns) or imposto.find('.//PIS')
        if pis_elem is None:
            return {}
        
        # PISAliq, PISOutr ou PISNT
        pis_aliq = pis_elem.find('.//nfe:PISAliq', ns) or pis_elem.find('.//PISAliq')
        pis_outr = pis_elem.find('.//nfe:PISOutr', ns) or pis_elem.find('.//PISOutr')
        pis_nt = pis_elem.find('.//nfe:PISNT', ns) or pis_elem.find('.//PISNT')
        
        cst = bc = aliq = vlr = None
        
        for elem in [pis_aliq, pis_outr, pis_nt]:
            if elem is not None:
                cst = cst or self.get_text(elem, './/nfe:CST', ns) or self.get_text(elem, './/CST')
                bc = bc or self.get_text(elem, './/nfe:vBC', ns) or self.get_text(elem, './/vBC')
                aliq = aliq or self.get_text(elem, './/nfe:pPIS', ns) or self.get_text(elem, './/pPIS')
                vlr = vlr or self.get_text(elem, './/nfe:vPIS', ns) or self.get_text(elem, './/vPIS')
        
        return {
            'CST Pis': cst,
            'BC Pis': bc,
            'Alíq. Pis': aliq,
            'Vlr Pis': vlr
        }
    
    def _extract_cofins(self, imposto, ns) -> Dict:
        """Extrai dados de COFINS"""
        cofins_elem = imposto.find('.//nfe:COFINS', ns) or imposto.find('.//COFINS')
        if cofins_elem is None:
            return {}
        
        # COFINSAliq, COFINSOutr ou COFINSNT
        cofins_aliq = cofins_elem.find('.//nfe:COFINSAliq', ns) or cofins_elem.find('.//COFINSAliq')
        cofins_outr = cofins_elem.find('.//nfe:COFINSOutr', ns) or cofins_elem.find('.//COFINSOutr')
        cofins_nt = cofins_elem.find('.//nfe:COFINSNT', ns) or cofins_elem.find('.//COFINSNT')
        
        cst = bc = aliq = vlr = None
        
        for elem in [cofins_aliq, cofins_outr, cofins_nt]:
            if elem is not None:
                cst = cst or self.get_text(elem, './/nfe:CST', ns) or self.get_text(elem, './/CST')
                bc = bc or self.get_text(elem, './/nfe:vBC', ns) or self.get_text(elem, './/vBC')
                aliq = aliq or self.get_text(elem, './/nfe:pCOFINS', ns) or self.get_text(elem, './/pCOFINS')
                vlr = vlr or self.get_text(elem, './/nfe:vCOFINS', ns) or self.get_text(elem, './/vCOFINS')
        
        return {
            'CST Cofins': cst,
            'BC Cofins': bc,
            'Alíq. Cofins': aliq,
            'Vlr Cofins': vlr
        }
    
    def process_cte_file(self, xml_path: Path) -> List[Dict]:
        """
        Processa arquivo CTe baseado no script M fornecido
        Retorna lista de dicionários (normalmente 1 por CTe)
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            ns = self.NAMESPACES
            
            # Busca CTe
            cte_elem = root.find('.//cte:CTe', ns) or root.find('.//CTe')
            if cte_elem is None:
                return []
            
            inf_cte = cte_elem.find('.//cte:infCte', ns) or cte_elem.find('.//infCte')
            if inf_cte is None:
                return []
            
            # Chave CTe
            chave_cte = inf_cte.get('Id', '').replace('CTe', '')
            
            # IDE - Identificação
            ide = inf_cte.find('.//cte:ide', ns) or inf_cte.find('.//ide')
            cfop = self.get_text(ide, './/cte:CFOP', ns) or self.get_text(ide, './/CFOP')
            nat_op = self.get_text(ide, './/cte:natOp', ns) or self.get_text(ide, './/natOp')
            serie = self.get_text(ide, './/cte:serie', ns) or self.get_text(ide, './/serie')
            num_cte = self.get_text(ide, './/cte:nCT', ns) or self.get_text(ide, './/nCT')
            dh_emi = self.get_text(ide, './/cte:dhEmi', ns) or self.get_text(ide, './/dhEmi')
            tp_cte = self.get_text(ide, './/cte:tpCTe', ns) or self.get_text(ide, './/tpCTe')
            tp_serv = self.get_text(ide, './/cte:tpServ', ns) or self.get_text(ide, './/tpServ')
            
            # Municípios
            mun_ini = self.get_text(ide, './/cte:xMunIni', ns) or self.get_text(ide, './/xMunIni')
            uf_ini = self.get_text(ide, './/cte:UFIni', ns) or self.get_text(ide, './/UFIni')
            mun_fim = self.get_text(ide, './/cte:xMunFim', ns) or self.get_text(ide, './/xMunFim')
            uf_fim = self.get_text(ide, './/cte:UFFim', ns) or self.get_text(ide, './/UFFim')
            
            # Tomador
            toma3 = ide.find('.//cte:toma3', ns) or ide.find('.//toma3')
            toma4 = ide.find('.//cte:toma4', ns) or ide.find('.//toma4')
            
            tomador = None
            if toma3 is not None:
                toma_cod = self.get_text(toma3, './/cte:toma', ns) or self.get_text(toma3, './/toma')
                tomador = toma_cod
            elif toma4 is not None:
                tomador = self.get_text(toma4, './/cte:CNPJ', ns) or self.get_text(toma4, './/CNPJ')
            
            # Converte tipo CTe
            tipo_cte_map = {'0': 'CTE Normal', '1': 'CTe Complemento', '3': 'CTe Substituto'}
            tipo_cte = tipo_cte_map.get(tp_cte, tp_cte)
            
            # Converte tipo serviço
            tipo_serv_map = {
                '0': 'Normal', '1': 'Subcontratação', '2': 'Redespacho',
                '3': 'Redespacho intermediário', '4': 'Serviço Vinculado à Multimodal'
            }
            tipo_servico = tipo_serv_map.get(tp_serv, tp_serv)
            
            # EMIT - Emitente
            emit = inf_cte.find('.//cte:emit', ns) or inf_cte.find('.//emit')
            cnpj_emit = self.get_text(emit, './/cte:CNPJ', ns) or self.get_text(emit, './/CNPJ')
            ie_emit = self.get_text(emit, './/cte:IE', ns) or self.get_text(emit, './/IE')
            nome_emit = self.get_text(emit, './/cte:xNome', ns) or self.get_text(emit, './/xNome')
            
            # REM - Remetente
            rem = inf_cte.find('.//cte:rem', ns) or inf_cte.find('.//rem')
            cnpj_rem = self.get_text(rem, './/cte:CNPJ', ns) or self.get_text(rem, './/CNPJ')
            ie_rem = self.get_text(rem, './/cte:IE', ns) or self.get_text(rem, './/IE')
            nome_rem = self.get_text(rem, './/cte:xNome', ns) or self.get_text(rem, './/xNome')
            
            # DEST - Destinatário
            dest = inf_cte.find('.//cte:dest', ns) or inf_cte.find('.//dest')
            cnpj_dest = self.get_text(dest, './/cte:CNPJ', ns) or self.get_text(dest, './/CNPJ')
            ie_dest = self.get_text(dest, './/cte:IE', ns) or self.get_text(dest, './/IE')
            nome_dest = self.get_text(dest, './/cte:xNome', ns) or self.get_text(dest, './/xNome')
            
            # vPrest - Valor da Prestação
            vprest = inf_cte.find('.//cte:vPrest', ns) or inf_cte.find('.//vPrest')
            vlr_servico = self.get_text(vprest, './/cte:vTPrest', ns) or self.get_text(vprest, './/vTPrest')
            
            # IMP - Impostos
            imp = inf_cte.find('.//cte:imp', ns) or inf_cte.find('.//imp')
            icms = imp.find('.//cte:ICMS', ns) or imp.find('.//ICMS') if imp is not None else None
            
            # ICMS do CTe (múltiplos CSTs possíveis)
            icms_data = self._extract_cte_icms(icms, ns)
            
            # infCTeNorm - Informações Normais (NFe referenciada, CTe substituído)
            inf_cte_norm = inf_cte.find('.//cte:infCTeNorm', ns) or inf_cte.find('.//infCTeNorm')
            nf_ref = cte_subs = None
            
            if inf_cte_norm is not None:
                # NFe referenciada
                inf_doc = inf_cte_norm.find('.//cte:infDoc', ns) or inf_cte_norm.find('.//infDoc')
                if inf_doc is not None:
                    inf_nfe = inf_doc.find('.//cte:infNFe', ns) or inf_doc.find('.//infNFe')
                    if inf_nfe is not None:
                        nf_ref = self.get_text(inf_nfe, './/cte:chave', ns) or self.get_text(inf_nfe, './/chave')
                
                # CTe substituído
                inf_cte_sub = inf_cte_norm.find('.//cte:infCteSub', ns) or inf_cte_norm.find('.//infCteSub')
                if inf_cte_sub is not None:
                    cte_subs = self.get_text(inf_cte_sub, './/cte:chCte', ns) or self.get_text(inf_cte_sub, './/chCte')
            
            # Data emissão
            data_emissao = dh_emi.split('T')[0] if dh_emi and 'T' in dh_emi else dh_emi
            
            # Monta registro
            cte_data = {
                'CFOP': cfop,
                'NAT. Operação': nat_op,
                'Série': serie,
                'Número CTE': num_cte,
                'Data Emissão': data_emissao,
                'Tipo CTE': tipo_cte,
                'Tipo do serviço': tipo_servico,
                'Mun. Inicio': mun_ini,
                'UF Inicio': uf_ini,
                'Mun. Fim': mun_fim,
                'UF Fim': uf_fim,
                'Tomador': tomador,
                'CNPJ emit.': cnpj_emit,
                'IE. emit.': ie_emit,
                'Emitente': nome_emit,
                'CNPJ rem.': cnpj_rem,
                'IE. rem.': ie_rem,
                'Remetente': nome_rem,
                'CNPJ dest.': cnpj_dest,
                'IE. dest.': ie_dest,
                'Destinatário': nome_dest,
                'VLR Serviço': vlr_servico,
                **icms_data,
                'NF ref.': nf_ref,
                'Chave CT-e Subs': cte_subs,
                'Chave CTE': chave_cte
            }
            
            return [cte_data]
            
        except Exception as e:
            print(f"Erro ao processar CTe {xml_path}: {str(e)}")
            return []
    
    def _extract_cte_icms(self, icms, ns) -> Dict:
        """Extrai dados de ICMS do CTe"""
        if icms is None:
            return {}
        
        # CSTs possíveis no CTe
        cst_tags = ['ICMS00', 'ICMS20', 'ICMS45', 'ICMS60', 'ICMS90', 'ICMSSN', 'ICMSOutraUF']
        
        optante_sn = cst = bc = aliq = vlr = None
        
        for cst_tag in cst_tags:
            cst_elem = icms.find(f'.//cte:{cst_tag}', ns) or icms.find(f'.//{cst_tag}')
            if cst_elem is not None:
                cst = cst or self.get_text(cst_elem, './/cte:CST', ns) or self.get_text(cst_elem, './/CST')
                bc = bc or self.get_text(cst_elem, './/cte:vBC', ns) or self.get_text(cst_elem, './/vBC')
                aliq = aliq or self.get_text(cst_elem, './/cte:pICMS', ns) or self.get_text(cst_elem, './/pICMS')
                vlr = vlr or self.get_text(cst_elem, './/cte:vICMS', ns) or self.get_text(cst_elem, './/vICMS')
                
                # Simples Nacional
                if cst_tag == 'ICMSSN':
                    ind_sn = self.get_text(cst_elem, './/cte:indSN', ns) or self.get_text(cst_elem, './/indSN')
                    optante_sn = 'Sim' if ind_sn == '1' else 'Não'
                
                # Outra UF
                bc_outra = self.get_text(cst_elem, './/cte:vBCOutraUF', ns) or self.get_text(cst_elem, './/vBCOutraUF')
                aliq_outra = self.get_text(cst_elem, './/cte:pICMSOutraUF', ns) or self.get_text(cst_elem, './/pICMSOutraUF')
                vlr_outra = self.get_text(cst_elem, './/cte:vICMSOutraUF', ns) or self.get_text(cst_elem, './/vICMSOutraUF')
                
                bc = bc or bc_outra
                aliq = aliq or aliq_outra
                vlr = vlr or vlr_outra
        
        return {
            'Optante SN': optante_sn or 'Não',
            'CST': cst,
            'BC ICMS': bc,
            'Alíq. ICMS': aliq,
            'Vlr ICMS': vlr or '0'
        }
    
    def process_xml_folder(self, folder_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Processa pasta com XMLs mistos (NFe e CTe)
        Retorna: (df_nfe, df_cte)
        """
        xml_files = list(folder_path.glob('*.xml'))
        
        nfe_records = []
        cte_records = []
        
        for xml_file in xml_files:
            xml_type = self.detect_xml_type(xml_file)
            
            if xml_type == 'NFe':
                records = self.process_nfe_file(xml_file)
                nfe_records.extend(records)
            elif xml_type == 'CTe':
                records = self.process_cte_file(xml_file)
                cte_records.extend(records)
        
        df_nfe = pd.DataFrame(nfe_records) if nfe_records else pd.DataFrame()
        df_cte = pd.DataFrame(cte_records) if cte_records else pd.DataFrame()
        
        return df_nfe, df_cte
