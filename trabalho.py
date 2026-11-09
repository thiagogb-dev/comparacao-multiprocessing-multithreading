
import pandas as pd
import unicodedata
import time

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


NUM_WORKERS = 4


def normalizar(texto):
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFKD", texto)

    texto_sem_acento = ""

    for letra in texto:
        if not unicodedata.combining(letra):
            texto_sem_acento += letra

    return texto_sem_acento


def calcular_bloco(dados):

    votos = dados["QT_VOTOS_NOMINAIS_VALIDOS"]

    soma_votos = votos.sum()
    quantidade = votos.count()

    partidos = dados.groupby("SG_PARTIDO")[
        "QT_VOTOS_NOMINAIS_VALIDOS"
    ].agg(["sum", "count"])

    cargos = dados.groupby("DS_CARGO")[
        "QT_VOTOS_NOMINAIS_VALIDOS"
    ].agg(["sum", "count"])

    resultado = {
        "soma": soma_votos,
        "quantidade": quantidade,
        "partidos": partidos,
        "cargos": cargos
    }

    return resultado


def juntar_resultados(lista_resultados):

    soma_total = 0
    quantidade_total = 0

    lista_partidos = []
    lista_cargos = []

    for resultado in lista_resultados:

        soma_total += resultado["soma"]
        quantidade_total += resultado["quantidade"]

        lista_partidos.append(resultado["partidos"])
        lista_cargos.append(resultado["cargos"])

    partidos = pd.concat(lista_partidos)
    partidos = partidos.groupby(level=0).sum()

    cargos = pd.concat(lista_cargos)
    cargos = cargos.groupby(level=0).sum()

    media_geral = soma_total / quantidade_total

    media_partido = partidos["sum"] / partidos["count"]
    media_partido = media_partido.sort_values(ascending=False)

    media_cargo = cargos["sum"] / cargos["count"]
    media_cargo = media_cargo.sort_values(ascending=False)

    resultado_final = {
        "total": quantidade_total,
        "geral": media_geral,
        "partidos": media_partido,
        "cargos": media_cargo
    }

    return resultado_final


def mostrar_resultados(nome, resultado, tempo):

    print("\n==========", nome, "==========")

    print("\nTotal de registros:", resultado["total"])

    print("\nMedia geral:")
    print(round(resultado["geral"], 2))

    print("\nMedia por partido:")
    print(resultado["partidos"].round(2))

    print("\nPartido com maior media:")
    print(resultado["partidos"].idxmax())
    print("Media:", round(resultado["partidos"].max(), 2))

    print("\nMedia por cargo:")
    print(resultado["cargos"].round(2))

    print("\nCargo com maior media:")
    print(resultado["cargos"].idxmax())
    print("Media:", round(resultado["cargos"].max(), 2))

    print("\nTempo de execucao:")
    print(round(tempo, 6), "segundos")


def main():

    caminho = "dados/votacao_candidato_munzona_2026_SP.csv"

    dados = pd.read_csv(
        caminho,
        sep=";",
        encoding="latin-1"
    )

    dados["MUNICIPIO_NORMALIZADO"] = dados["NM_MUNICIPIO"].apply(normalizar)

    jundiai = dados[
        (dados["SG_UF"] == "SP") &
        (dados["MUNICIPIO_NORMALIZADO"] == "JUNDIAI")
    ].copy()

    # Garantir que os votos sejam numeros
    jundiai["QT_VOTOS_NOMINAIS_VALIDOS"] = pd.to_numeric(
        jundiai["QT_VOTOS_NOMINAIS_VALIDOS"],
        errors="coerce"
    )

    dados_calculo = jundiai[
        [
            "SG_PARTIDO",
            "DS_CARGO",
            "QT_VOTOS_NOMINAIS_VALIDOS"
        ]
    ].copy()

    if len(dados_calculo) == 0:
        print("Nenhum registro encontrado para Jundiai.")
        return

    # ---------------- SEQUENCIAL ----------------

    inicio = time.perf_counter()

    resultado = calcular_bloco(dados_calculo)
    resultado_sequencial = juntar_resultados([resultado])

    fim = time.perf_counter()
    tempo_sequencial = fim - inicio

    # Dividir os dados em quatro blocos
    tamanho_bloco = (len(dados_calculo) + NUM_WORKERS - 1) // NUM_WORKERS

    blocos = []

    for inicio_bloco in range(0, len(dados_calculo), tamanho_bloco):
        fim_bloco = inicio_bloco + tamanho_bloco
        bloco = dados_calculo.iloc[inicio_bloco:fim_bloco]
        blocos.append(bloco)

    # ---------------- MULTIPROCESSING ----------------

    inicio = time.perf_counter()

    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        resultados_processos = list(executor.map(calcular_bloco, blocos))

    resultado_multiprocessing = juntar_resultados(resultados_processos)

    fim = time.perf_counter()
    tempo_multiprocessing = fim - inicio

    # ---------------- MULTITHREADING ----------------

    inicio = time.perf_counter()

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        resultados_threads = list(executor.map(calcular_bloco, blocos))

    resultado_multithreading = juntar_resultados(resultados_threads)

    fim = time.perf_counter()
    tempo_multithreading = fim - inicio

    # Mostrar os resultados dos tres metodos

    mostrar_resultados(
        "RESULTADOS SEQUENCIAL",
        resultado_sequencial,
        tempo_sequencial
    )

    mostrar_resultados(
        "RESULTADOS MULTIPROCESSING",
        resultado_multiprocessing,
        tempo_multiprocessing
    )

    mostrar_resultados(
        "RESULTADOS MULTITHREADING",
        resultado_multithreading,
        tempo_multithreading
    )

    # Comparar os tempos

    print("\n========== COMPARACAO FINAL ==========")

    print("Sequencial:", round(tempo_sequencial, 6), "segundos")
    print("Multiprocessing:", round(tempo_multiprocessing, 6), "segundos")
    print("Multithreading:", round(tempo_multithreading, 6), "segundos")

    metodo_mais_rapido = "Sequencial"
    menor_tempo = tempo_sequencial

    if tempo_multiprocessing < menor_tempo:
        menor_tempo = tempo_multiprocessing
        metodo_mais_rapido = "Multiprocessing"

    if tempo_multithreading < menor_tempo:
        menor_tempo = tempo_multithreading
        metodo_mais_rapido = "Multithreading"

    print("\nMetodo mais rapido:", metodo_mais_rapido)


# Iniciar o programa
if __name__ == "__main__":
    main()