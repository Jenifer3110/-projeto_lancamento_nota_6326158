import csv
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_DIR = Path(__file__).parent
ARQUIVO_CSV = BASE_DIR / "notas.csv"

LINK_FORMULARIO = (
   "https://docs.google.com/forms/d/e/1FAIpQLSecZ46FOLWp1YTA5PB7Kvq36G6n_08XrT3Su9SSTaQx-33gTw/viewform?usp=header"
)

LIMITE_ALUNOS = 100


def carregar_alunos():
    with open(ARQUIVO_CSV, "r", encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def converter_nota(valor):
    valor = valor.strip().replace(",", ".")
    ausencias = {
        "FALTOU", "FALTA", "", "N/A", "-",
        "NÃƒO CONSTA", "NAO CONSTA",
        "SEM INFORMAÃ‡ÃƒO", "SEM INFORMACAO", "VAZIO"
    }
    if valor.upper() in ausencias:
        return 0.0
    return float(valor)


def calcular_notas(aluno):
    n1 = converter_nota(aluno["Nota01"])
    n2 = converter_nota(aluno["Nota02"])
    t1 = converter_nota(aluno["TF01"])
    t2 = converter_nota(aluno["TF02"])

    media_notas = (n1 + n2) / 2
    media_tf = (t1 + t2) / 2
    final = media_notas * 0.8 + media_tf * 0.2

    return n1, n2, t1, t2, final


def preencher_e_enviar(page, aluno, notas):
    nome = aluno["Nome"].strip()
    ra = aluno.get("RA", "").strip() or "0"
    n1, n2, t1, t2, final = notas

    page.goto(LINK_FORMULARIO, wait_until="domcontentloaded")
    page.get_by_role("textbox").nth(0).wait_for(state="visible", timeout=20000)

    campos = [ra, nome, f"{n1:.2f}", f"{n2:.2f}",
              f"{t1:.2f}", f"{t2:.2f}", f"{final:.2f}"]

    caixas = page.get_by_role("textbox")
    if caixas.count() < len(campos):
        raise RuntimeError(
            f"Esperava 7 campos no formulÃ¡rio, mas encontrei {caixas.count()}."
        )

    for i, valor in enumerate(campos):
        caixas.nth(i).fill(valor)

    page.get_by_role("button", name="Enviar").click()
    page.get_by_text("Sua resposta foi registrada", exact=False).wait_for(
        state="visible", timeout=20000
    )

    print(f"Resposta confirmada: {nome} | Nota final: {final:.2f}")


def main():
    try:
        alunos = carregar_alunos()
        preparados = [(aluno, calcular_notas(aluno)) for aluno in alunos]
    except (OSError, ValueError, KeyError) as erro:
        print(f"Erro ao ler o CSV ou calcular notas: {erro}")
        return

    if not preparados:
        print("Nenhum aluno encontrado.")
        return

    quantidade = min(LIMITE_ALUNOS, len(preparados))
    print(f"Alunos no processamento desta execuÃ§Ã£o: {quantidade}")
    print("O navegador serÃ¡ aberto para enviar as respostas automaticamente.")
    print("NÃ£o execute outra instÃ¢ncia do programa ao mesmo tempo.")

    resposta = input("Digite SIM para iniciar: ")
    if resposta.strip().upper() != "SIM":
        print("OperaÃ§Ã£o cancelada.")
        return

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)
        page = navegador.new_page()

        try:
            for indice, (aluno, notas) in enumerate(preparados[:quantidade], start=1):
                print(f"\nProcessando {indice}/{quantidade}: {aluno['Nome']}")

                try:
                    preencher_e_enviar(page, aluno, notas)
                except (PlaywrightTimeoutError, RuntimeError) as erro:
                    print(f"PARADO por seguranÃ§a em {aluno['Nome']}: {erro}")
                    print("Confira o formulÃ¡rio no navegador antes de tentar novamente.")
                    return

                time.sleep(1)

            print("\nProcessamento concluÃ­do.")
        finally:
            input("Pressione ENTER para fechar o navegador...")
            navegador.close()


if __name__ == "__main__":
    main()

