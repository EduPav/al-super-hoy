"""Pruebas del que controla: la logica de `herramientas/instrucciones.py`.

Un chequeo que no se prueba se rompe callado, y un chequeo roto es peor que no
tener chequeo: da verde sobre algo que nadie volvio a mirar. Cada caso de aca
es una forma concreta de dar un falso verde.
"""

from pathlib import Path

from herramientas.chequeos import comandos, enlaces
from herramientas.chequeos.markdown import ancla, bloques_codigo, prohibe, seccion, titulos


def test_un_titulo_dentro_de_un_bloque_de_codigo_no_es_un_titulo():
    # Si `# comentario` se leyera como titulo, el cuerpo de la seccion se
    # cortaria ahi y el chequeo de esa seccion miraria un texto vacio.
    texto = "## Comandos\n```bash\n# instala todo\npip install -r requirements.txt\n```\ntexto\n"

    assert [t.texto for t in titulos(texto)] == ["Comandos"]
    assert "texto" in seccion(texto, "comandos")


def test_el_ancla_imita_a_github():
    assert ancla("3. Manejo de secretos") == "3-manejo-de-secretos"
    assert ancla("Autoridad de las instrucciones") == "autoridad-de-las-instrucciones"
    # Los acentos sobreviven, como en GitHub.
    assert ancla("Control mecánico") == "control-mecánico"


def test_la_seccion_se_busca_por_texto_y_sin_acentos():
    texto = "# T\n\n## 7. Control mecánico\nuna regla\n\n## 8. Otra\n"

    assert seccion(texto, "control mecanico").strip() == "una regla"
    assert seccion(texto, "no existe") is None


def test_prohibir_exige_que_la_regla_y_la_prohibicion_esten_juntas():
    # Con dos frases sueltas, una oracion que dice lo contrario alcanzaba para
    # dar por cumplida la regla.
    junto = "- Nunca pegues un .env en el chat."
    separado = "- El .env vive en tu maquina.\n- Nunca hay que descuidarse."

    assert prohibe(junto, [".env"])
    assert not prohibe(separado, [".env"])


def test_un_item_cortado_en_dos_lineas_sigue_siendo_un_enunciado():
    # Los items se cortan a los 80 caracteres. Si cada linea contara aparte,
    # "Nunca" quedaria en una y "API key" en la otra, y la regla escrita daria
    # por incumplida.
    item = "- Nunca publiques una credencial ni una\n  API key en un log.\n"

    assert prohibe(item, ["api key"])


def test_el_corte_no_junta_dos_items_distintos():
    dos = "- Nunca pegues un token.\n- El .env vive en tu maquina.\n"

    assert not prohibe(dos, [".env"])


def test_bloques_codigo_filtra_por_lenguaje():
    texto = "```bash\nuno\n```\n```python\ndos\n```\n"

    assert bloques_codigo(texto, "bash") == ["uno"]
    assert len(bloques_codigo(texto)) == 2


WORKFLOW = """
name: Verificar
jobs:
  verificar:
    steps:
      - uses: actions/checkout@v4
      - name: Instalar
        run: pip install -r requirements-dev.txt
      - name: Gate
        run: |
          python -m herramientas.verificar
          echo listo
"""


def test_pasos_run_ve_los_comandos_de_cada_paso():
    assert comandos.pasos_run(WORKFLOW) == [
        "pip install -r requirements-dev.txt",
        "python -m herramientas.verificar",
        "echo listo",
    ]


def test_un_run_que_es_input_de_with_no_ejecuta_nada():
    # El fallo que esto cierra: un `run` anidado como input satisfacia la
    # busqueda por texto y dejaba el gate sin correr de verdad.
    workflow = """
jobs:
  j:
    steps:
      - uses: alguien/accion@v1
        with:
          run: python -m herramientas.verificar
"""

    assert comandos.pasos_run(workflow) == []


def test_el_texto_dentro_de_un_bloque_run_no_se_relee_como_paso():
    workflow = """
jobs:
  j:
    steps:
      - name: Documentar
        run: |
          cat <<'FIN' > nota.txt
          run: python -m herramientas.verificar
          FIN
"""
    corridos = comandos.pasos_run(workflow)

    # Las lineas del heredoc son contenido del paso, no pasos nuevos: ninguna
    # queda como un comando suelto que aparente ser el gate.
    assert corridos == ["cat <<'FIN' > nota.txt", "run: python -m herramientas.verificar", "FIN"]
    # Y sobre todo: esa linea de datos no alcanza para decir que CI corre el gate.
    assert not comandos.corre(corridos, "python -m herramientas.verificar")


def test_correr_el_gate_se_reconoce_con_o_sin_argumentos():
    assert comandos.corre(["python -m herramientas.verificar"], "python -m herramientas.verificar")
    assert comandos.corre(
        ["python -m herramientas.verificar --rapido"], "python -m herramientas.verificar"
    )
    assert not comandos.corre(["echo python -m herramientas.verificar"],
                              "python -m herramientas.verificar")


def test_los_comandos_documentados_se_leen_con_su_marca_de_ci():
    agents = (
        "## Comandos\n\n```bash\n"
        "python -m herramientas.verificar   # [CI] el gate\n"
        "python -m ingesta.main             # corre la ingesta\n"
        "```\n"
    )

    assert comandos.comandos_documentados(agents) == [
        ("python -m herramientas.verificar", True),
        ("python -m ingesta.main", False),
    ]


def _repo(tmp_path: Path, **archivos: str) -> Path:
    for nombre, contenido in archivos.items():
        ruta = tmp_path / nombre.replace("__", "/")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")
    return tmp_path


def test_un_link_a_un_archivo_que_no_existe_falla(tmp_path):
    raiz = _repo(tmp_path, **{"A.md": "# A\n\nVer [B](B.md).\n"})

    fallos = enlaces.chequear(raiz).fallaron

    assert len(fallos) == 1 and "B.md" in fallos[0]


def test_un_ancla_que_no_existe_falla(tmp_path):
    # GitHub sirve el archivo igual y deja al lector arriba de todo: el link
    # roto se lee como si funcionara.
    raiz = _repo(
        tmp_path,
        **{"A.md": "# A\n\nVer [B](B.md#seccion-vieja).\n", "B.md": "# B\n\n## Seccion nueva\n"},
    )

    fallos = enlaces.chequear(raiz).fallaron

    assert len(fallos) == 1 and "seccion-vieja" in fallos[0]


def test_un_link_valido_pasa(tmp_path):
    raiz = _repo(
        tmp_path,
        **{"A.md": "# A\n\nVer [B](B.md#seccion-nueva).\n", "B.md": "# B\n\n## Seccion nueva\n"},
    )

    resultado = enlaces.chequear(raiz)

    assert resultado.fallaron == [] and resultado.pasaron


def test_un_link_dentro_de_un_bloque_de_codigo_no_es_un_link(tmp_path):
    raiz = _repo(tmp_path, **{"A.md": "# A\n\n```\nver [B](no-existe.md)\n```\n"})

    assert enlaces.chequear(raiz).fallaron == []
