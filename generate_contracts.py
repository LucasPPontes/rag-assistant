import os

def create_pdf(filepath, title, content_lines):
    """Gera um arquivo PDF 1.4 válido sem dependências externas."""
    # Sanitização simples para codificação PDF Type1 Helvetica
    def clean_str(s):
        replacements = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
            'é': 'e', 'ê': 'e', 'í': 'i', 'ó': 'o', 'ô': 'o',
            'õ': 'o', 'ú': 'u', 'ç': 'c', 'Á': 'A', 'É': 'E',
            'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ç': 'C', 'R$': 'RS'
        }
        for k, v in replacements.items():
            s = s.replace(k, v)
        return s.replace("(", "\\(").replace(")", "\\)")

    clean_title = clean_str(title)
    
    stream_ops = []
    stream_ops.append("BT")
    stream_ops.append("/F1 14 Tf")
    stream_ops.append("50 770 Td")
    stream_ops.append(f"({clean_title}) Tj")
    stream_ops.append("/F1 10 Tf")
    stream_ops.append("0 -30 Td")

    for line in content_lines:
        c_line = clean_str(line)
        if not c_line.strip():
            stream_ops.append("0 -12 Td")
        else:
            stream_ops.append(f"({c_line}) Tj")
            stream_ops.append("0 -15 Td")
            
    stream_ops.append("ET")
    stream_content = "\n".join(stream_ops)
    stream_bytes = stream_content.encode('latin1')
    stream_len = len(stream_bytes)

    pdf_body = (
        f"%PDF-1.4\n"
        f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        f"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        f"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 595 842] /Contents 5 0 R >>\nendobj\n"
        f"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        f"5 0 obj\n<< /Length {stream_len} >>\nstream\n"
    ).encode('latin1') + stream_bytes + b"\nendstream\nendobj\n"

    # offsets para tabela xref
    pos1 = pdf_body.find(b"1 0 obj")
    pos2 = pdf_body.find(b"2 0 obj")
    pos3 = pdf_body.find(b"3 0 obj")
    pos4 = pdf_body.find(b"4 0 obj")
    pos5 = pdf_body.find(b"5 0 obj")
    xref_pos = len(pdf_body)

    xref = (
        f"xref\n0 6\n"
        f"0000000000 65535 f \n"
        f"{pos1:010d} 00000 n \n"
        f"{pos2:010d} 00000 n \n"
        f"{pos3:010d} 00000 n \n"
        f"{pos4:010d} 00000 n \n"
        f"{pos5:010d} 00000 n \n"
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode('latin1')

    with open(filepath, "wb") as f:
        f.write(pdf_body + xref)

    print(f"✅ PDF criado: {filepath}")

# Diretório de destino
output_dir = "/home/lucas/Área de trabalho/rag_assistent/exemplos_contratos"
os.makedirs(output_dir, exist_ok=True)

# 1. Contrato de Prestacao de Servicos
c1_title = "CONTRATO DE PRESTACAO DE SERVICOS DE TECNOLOGIA"
c1_content = [
    "CONTRATANTE: TechSolutions Tecnologia Ltda, CNPJ 12.345.678/0001-90.",
    "CONTRATADO: Joao da Silva Consultoria MEI, CNPJ 98.765.432/0001-10.",
    "",
    "CLAVSULA PRIMEIRA - DO OBJETO",
    "O presente contrato tem como objeto a prestacao de servicos de desenvolvimento",
    "de software, manutencao de banco de dados e integracao de sistemas RAG de IA.",
    "",
    "CLAVSULA SEGUNDA - DO VALOR E VALOR MENSAL",
    "Pelo cumprimento dos servicos contratados, a CONTRATANTE pagara ao CONTRATADO",
    "o valor mensalde RS 15.000,00 (quinze mil reais), com vencimento todo dia 05.",
    "",
    "CLAVSULA TERCEIRA - DA VIGENCIA",
    "O contrato tera vigencia de 12 (doze) meses, iniciando em 01/01/2026 e",
    "encerrando-se em 31/12/2026, podendo ser renovado mediante aditivo escrito.",
    "",
    "CLAVSULA QUARTA - DA RESCISAO E MULTA",
    "A rescisao antecipada sem aviso previo de 30 dias implicara multa rescisoria de 20%",
    "sobre o valor restante devido do contrato."
]

# 2. Contrato de Aluguel Comercial
c2_title = "CONTRATO DE LOCACAO DE IMOVEL COMERCIAL"
c2_content = [
    "LOCADOR: Imobiliaria Alvorada S.A., CNPJ 44.333.222/0001-55.",
    "LOCATARIO: Startup Inovacao & IA Ltda, CNPJ 55.666.777/0001-88.",
    "",
    "CLAVSULA PRIMEIRA - DO IMOVEL",
    "O LOCADOR cede para uso comercial a sala numero 502, situada na Av. Paulista, 1000,",
    "Sao Paulo - SP.",
    "",
    "CLAVSULA SEGUNDA - DO ALUGUEL E CONDOMINIO",
    "O valor do aluguel mensal ajustado e de RS 8.500,00 (oito mil e quinhentos reais),",
    "acrescido da taxa condominial estipulada em RS 1.200,00 mensais.",
    "",
    "CLAVSULA TERCEIRA - DO REAJUSTE ANUAL",
    "O valor do aluguel sera reajustado anualmente com base na variacao positiva do IPCA/IBGE.",
    "",
    "CLAVSULA QUARTA - DA GARANTIA LOCATICIA",
    "Como garantia locaticia, foi prestada caucao no valor equivalente a 3 meses de aluguel,",
    "perfazendo o montante total de RS 25.500,00."
]

# 3. Contrato NDA (Confidencialidade)
c3_title = "ACORDO DE CONFIDENCIALIDADE E NAO DIVULGACAO (NDA)"
c3_content = [
    "PARTE REVELADORA: Alpha Corp Tecnologia S.A.",
    "PARTE RECEPTORA: Beta Innovations Inteligencia Artificial Ltda.",
    "",
    "CLAVSULA PRIMEIRA - DAS INFORMACOES CONFIDENCIAIS",
    "Sao consideradas informacoes confidenciais todos os dados tecnicos, codigos-fonte,",
    "arquiteturas de sistemas RAG, algoritmos e dados de clientes compartilhados.",
    "",
    "CLAVSULA SEGUNDA - DO PRAZO DE CONFIDENCIALIDADE",
    "As partes se obrigam a manter sigilo rigoroso pelo prazo de 5 (cinco) anos a contar",
    "da data de assinatura deste instrumento.",
    "",
    "CLAVSULA TERCEIRA - DA PENALIDADE",
    "A divulgacao nao autorizada sujeitara a parte infratora ao pagamento de multa",
    "penal compensatoria no valor de RS 100.000,00 (cem mil reais)."
]

create_pdf(os.path.join(output_dir, "contrato_prestacao_servicos.pdf"), c1_title, c1_content)
create_pdf(os.path.join(output_dir, "contrato_aluguel_comercial.pdf"), c2_title, c2_content)
create_pdf(os.path.join(output_dir, "contrato_nda_confidencialidade.pdf"), c3_title, c3_content)
