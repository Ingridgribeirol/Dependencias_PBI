
def calcular_complexity_score(expressao, nome_medida, medidas_dependentes=0):
    """
    Calcula Complexity Score (0-100) com 5 dimensões baseado em SQLBI + Microsoft Learn.
    
    Args:
        expressao: Expressão DAX
        nome_medida: Nome da medida
        medidas_dependentes: Número de medidas que dependem desta
    
    Returns:
        (score, classificacao, detalhes)
    """
    import re
    
    if not expressao or expressao == "":
        return 0, "🟢 Simples", []
    
    score = 0
    detalhes = []
    
    # === D1: FUNÇÕES (Peso Alto) ===
    funcoes_peso = {
        'SUMX': 8, 'AVERAGEX': 8, 'MINX': 8, 'MAXX': 8,
        'RANKX': 12,
        'FILTER': 10,
        'ADDCOLUMNS': 10,
        'SUMMARIZE': 12, 'SUMMARIZECOLUMNS': 12,
        'GENERATE': 15,
        'EARLIER': 20,
        'PATH': 8, 'CONTAINSROW': 8
    }
    
    for func, penalty in funcoes_peso.items():
        count = expressao.upper().count(func)
        if count > 0:
            score += count * penalty
            detalhes.append(f"D1: {func} ({count}x) = +{count * penalty}")
    
    # === D2: CALCULATE E CONTEXTO ===
    calculate_count = expressao.upper().count('CALCULATE')
    if calculate_count > 0:
        score += calculate_count * 5
        detalhes.append(f"D2: CALCULATE ({calculate_count}x) = +{calculate_count * 5}")
    
    # Múltiplos filtros em CALCULATE (heurística: vírgulas dentro de CALCULATE)
    calc_pattern = r'CALCULATE\s*\([^,]+,([^)]+)\)'
    for match in re.findall(calc_pattern, expressao, re.IGNORECASE):
        filters = match.count(',') + 1
        if filters > 1:
            penalty = (filters - 1) * 3
            score += penalty
            detalhes.append(f"D2: CALCULATE c/ {filters} filtros = +{penalty}")
    
    # ALL, ALLEXCEPT, REMOVEFILTERS
    context_funcs = {'ALL': 6, 'ALLEXCEPT': 6, 'REMOVEFILTERS': 6, 'KEEPFILTERS': 3}
    for func, penalty in context_funcs.items():
        count = expressao.upper().count(func)
        if count > 0:
            score += count * penalty
            detalhes.append(f"D2: {func} ({count}x) = +{count * penalty}")
    
    # === D3: ESTRUTURA ===
    linhas = expressao.count('\n') + 1
    if linhas > 20:
        score += 10
        detalhes.append(f"D3: >20 linhas ({linhas}) = +10")
    elif linhas > 10:
        score += 5
        detalhes.append(f"D3: >10 linhas ({linhas}) = +5")
    
    # Bônus: VAR
    if 'VAR' in expressao.upper():
        var_count = expressao.upper().count('VAR')
        bonus = var_count * 5
        score -= bonus
        detalhes.append(f"D3: VAR ({var_count}x) = -{bonus} (bônus)")
    
    # Bônus: Comentários
    comentarios = expressao.count('--') + expressao.count('//')
    if comentarios > 0:
        bonus = min(comentarios * 2, 10)  # Max 10 pontos bônus
        score -= bonus
        detalhes.append(f"D3: Comentários ({comentarios}) = -{bonus} (bônus)")
    
    # === D4: DEPENDÊNCIAS ===
    if medidas_dependentes > 0:
        penalty = medidas_dependentes * 2
        score += penalty
        detalhes.append(f"D4: {medidas_dependentes} dependentes = +{penalty}")
    
    # === D5: ANTI-PATTERNS ===
    
    # FILTER(ALL(Tabela), ...)
    if re.search(r'FILTER\s*\(\s*ALL\s*\(', expressao, re.IGNORECASE):
        score += 20
        detalhes.append("D5: FILTER(ALL(Tabela)) = +20")
    
    # Time intelligence manual
    if 'DATE' in expressao.upper() and not any(x in expressao.upper() for x in ['SAMEPERIODLASTYEAR', 'DATESYTD', 'TOTALYTD', 'DATEADD']):
        score += 8
        detalhes.append("D5: Time intelligence manual = +8")
    
    # === CLASSIFICAÇÃO ===
    final_score = min(100, max(0, score))
    
    if final_score <= 20:
        classificacao = "🟢 Simples"
    elif final_score <= 40:
        classificacao = "🟡 Moderada"
    elif final_score <= 60:
        classificacao = "🟠 Complexa"
    elif final_score <= 80:
        classificacao = "🔴 Muito Complexa"
    else:
        classificacao = "⚫ Crítica"
    
    return final_score, classificacao, detalhes
