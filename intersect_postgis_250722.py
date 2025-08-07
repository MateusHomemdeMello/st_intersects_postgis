import sys
import json
import psycopg2
import geopandas as gpd
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QComboBox, QFileDialog,
    QTabWidget, QWidget, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QFrame, QTextEdit
)
from shapely.geometry import mapping, shape
from PyQt6.QtCore import Qt

DARK_STYLE = """
QWidget {
    background-color: #232629;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10.5pt;
}
QLineEdit, QComboBox, QTreeWidget, QTabWidget, QTableWidget, QTextEdit {
    background-color: #31363b;
    color: #e0e0e0;
    border: 1px solid #444;
    border-radius: 4px;
}
QPushButton {
    background-color: #3daee9;
    color: #232629;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #6cc7f7;
}
QPushButton:pressed {
    background-color: #2d8abf;
}
QLabel {
    color: #e0e0e0;
}
QTabBar::tab {
    background: #31363b;
    color: #e0e0e0;
    padding: 8px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #3daee9;
    color: #232629;
}
QTreeWidget::item:selected {
    background: #3daee9;
    color: #232629;
}
QMessageBox {
    background-color: #232629;
    color: #e0e0e0;
}
"""

class AbaConexaoPostgre(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conexão e Consulta Espacial")
        self.resize(600, 600)
        self.setMinimumWidth(520)
        # Adicione esta linha para garantir todos os botões da janela:
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        self.conn = None
        self.credenciais = {}
        self.aoi_info = {}

        self.tabs = QTabWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.tabs)

        # Abas
        self.tab_input = QWidget()
        self.tab_visualizacao = QWidget()

        # Layout da aba de visualização
        self.visualizacao_layout = QVBoxLayout(self.tab_visualizacao)
        self.tab_visualizacao.setLayout(self.visualizacao_layout)

        self.tree_resultados = QTreeWidget()
        self.tree_resultados.setHeaderLabels(["Camada"])  # Removido "Campo"
        self.visualizacao_layout.addWidget(self.tree_resultados)

        botoes_visualizacao = QHBoxLayout()

        self.diagnostico_btn = QPushButton("Diagnóstico")
        self.diagnostico_btn.setMinimumHeight(32)
        self.diagnostico_btn.setEnabled(False)
        self.diagnostico_btn.clicked.connect(self.exportar_csv_diagnostico)

        self.exportar_gpkg_btn = QPushButton("Exportar GeoPackage")
        self.exportar_gpkg_btn.setMinimumHeight(32)
        self.exportar_gpkg_btn.clicked.connect(self.exportar_geopackage_final)

        botoes_visualizacao.addWidget(self.diagnostico_btn)
        botoes_visualizacao.addWidget(self.exportar_gpkg_btn)
        botoes_visualizacao.addStretch()

        self.visualizacao_layout.addLayout(botoes_visualizacao)

        self.tabs.addTab(self.tab_input, "Entrada")
        self.tabs.addTab(self.tab_visualizacao, "Visualização")
        self.tabs.setTabVisible(1, False)

        # Layout da aba de entrada
        self.input_layout = QVBoxLayout(self.tab_input)
        self.tab_input.setLayout(self.input_layout)

        # Título principal: DIGLET
        titulo_diglet = QLabel("DIGLET")
        titulo_diglet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo_diglet.setStyleSheet("""
            font-size: 24pt;
            font-weight: bold;
            color: #3daee9;
            margin-top: 12px;
        """)

        # Subtítulo: sigla por extenso
        subtitulo = QLabel("Diagnóstico Interativo de Geoinformação e Levantamento Espacial Territorial")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setStyleSheet("""
            font-size: 10.5pt;
            color: #e0e0e0;
            margin-bottom: 12px;
        """)

        # Adiciona ao layout
        self.input_layout.addWidget(titulo_diglet)
        self.input_layout.addWidget(subtitulo)

        # Entradas de conexão em grid compacto
        grid = QHBoxLayout()
        self.host_input = QLineEdit(); self.host_input.setPlaceholderText("Host")
        self.port_input = QLineEdit(); self.port_input.setPlaceholderText("Porta"); self.port_input.setText("5432")
        self.db_input = QLineEdit(); self.db_input.setPlaceholderText("Banco")
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("Usuário")
        self.pass_input = QLineEdit(); self.pass_input.setPlaceholderText("Senha"); self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        for w in [self.host_input, self.port_input, self.db_input, self.user_input, self.pass_input]:
            w.setMaximumWidth(120)
            grid.addWidget(w)
        self.input_layout.addLayout(grid)

        # Botões de importação/exportação JSON em linha
        btns_json = QHBoxLayout()
        self.importar_json_btn = QPushButton("Importar JSON")
        self.importar_json_btn.setToolTip("Importar credenciais do arquivo JSON")
        self.importar_json_btn.clicked.connect(self.importar_credenciais_json)
        self.exportar_json_btn = QPushButton("Exportar JSON")
        self.exportar_json_btn.setToolTip("Exportar credenciais para arquivo JSON")
        self.exportar_json_btn.clicked.connect(self.exportar_credenciais_json)
        btns_json.addWidget(self.importar_json_btn)
        btns_json.addWidget(self.exportar_json_btn)
        btns_json.addStretch()
        self.input_layout.addLayout(btns_json)

        # Botão de conexão
        self.connect_button = QPushButton("Conectar")
        self.connect_button.setMinimumHeight(28)
        self.connect_button.clicked.connect(self.conectar_banco)
        self.input_layout.addWidget(self.connect_button)

        # Linha separadora
        self.input_layout.addWidget(self._linha())

        # ComboBox de esquemas (mais larga)
        schema_row = QHBoxLayout()
        self.schema_label = QLabel("Esquema:")
        self.schema_combo = QComboBox()
        self.schema_combo.setMinimumWidth(350)
        self.schema_combo.setSizePolicy(self.schema_combo.sizePolicy().horizontalPolicy(), self.schema_combo.sizePolicy().verticalPolicy())
        self.schema_combo.setEnabled(False)
        schema_row.addWidget(self.schema_label)
        schema_row.addWidget(self.schema_combo, stretch=1)
        self.input_layout.addLayout(schema_row)

        # Seletor de GeoJSON
        geo_row = QHBoxLayout()
        self.geojson_label = QLabel("AOI (GeoJSON):")
        self.geojson_input = QLineEdit(); self.geojson_input.setReadOnly(True)
        self.geojson_btn = QPushButton("Selecionar")
        self.geojson_btn.setMaximumWidth(90)
        self.geojson_btn.clicked.connect(self.selecionar_geojson)
        geo_row.addWidget(self.geojson_label)
        geo_row.addWidget(self.geojson_input)
        geo_row.addWidget(self.geojson_btn)
        self.input_layout.addLayout(geo_row)

        # Botões principais em linha
        btns_main = QHBoxLayout()
        self.buscar_tabelas_btn = QPushButton("Buscar Tabelas")
        self.buscar_tabelas_btn.clicked.connect(self.listar_tabelas_do_esquema)
        self.buscar_tabelas_btn.setEnabled(False)
        self.executar_intersecoes_btn = QPushButton("Executar Intersecção")
        self.executar_intersecoes_btn.clicked.connect(self.executar_st_intersect)
        self.executar_intersecoes_btn.setEnabled(False)
        for b in [self.buscar_tabelas_btn, self.executar_intersecoes_btn]:
            b.setMinimumHeight(28)
            btns_main.addWidget(b)
        btns_main.addStretch()
        self.input_layout.addLayout(btns_main)

        # Log de operações
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(110)
        self.log_box.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 10pt;")
        self.input_layout.addWidget(self.log_box)

        self.input_layout.addStretch()

    def _linha(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #444; margin: 8px 0;")
        return line

    def log(self, msg):
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def importar_credenciais_json(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo JSON", "", "JSON (*.json)")
        if not caminho:
            return
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            chaves = {"host", "port", "dbname", "user", "password"}
            if not chaves.issubset(dados.keys()):
                QMessageBox.warning(self, "Erro", "Arquivo JSON inválido ou incompleto.")
                return
            self.host_input.setText(dados["host"])
            self.port_input.setText(str(dados["port"]))
            self.db_input.setText(dados["dbname"])
            self.user_input.setText(dados["user"])
            self.pass_input.setText(dados["password"])
            self.credenciais = {
                "host": dados["host"],
                "port": str(dados["port"]),
                "dbname": dados["dbname"],
                "user": dados["user"],
                "password": dados["password"]
            }
            self.log(f"[Import] Credenciais carregadas: {self.credenciais}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler o JSON:\n{e}")

    def exportar_credenciais_json(self):
        dados = {
            "host": self.host_input.text(),
            "port": self.port_input.text(),
            "dbname": self.db_input.text(),
            "user": self.user_input.text(),
            "password": self.pass_input.text()
        }
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar arquivo JSON", "", "JSON (*.json)")
        if not caminho:
            return
        try:
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Exportado", "Credenciais salvas com sucesso!")
            self.log(f"[Export] Credenciais exportadas: {dados}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar JSON:\n{e}")

    def conectar_banco(self):
        self.credenciais = {
            "host": self.host_input.text(),
            "port": self.port_input.text(),
            "dbname": self.db_input.text(),
            "user": self.user_input.text(),
            "password": self.pass_input.text()
        }
        try:
            self.conn = psycopg2.connect(**self.credenciais)
            QMessageBox.information(self, "Conexão", "Conectado ao banco com sucesso!")
            self.log(f"[Conexão] Credenciais: {self.credenciais}")
            self.preencher_combobox_esquemas()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao conectar:\n{e}")
            self.log(f"[Erro] Falha ao conectar: {e}")

    def preencher_combobox_esquemas(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT schema_name FROM information_schema.schemata;")
            esquemas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            ignorar = {"pg_catalog", "information_schema"}
            esquemas_validos = sorted([e for e in esquemas if e not in ignorar])
            self.schema_combo.clear()
            self.schema_combo.addItems(esquemas_validos)
            self.schema_combo.setEnabled(True)
            self.buscar_tabelas_btn.setEnabled(True)
            self.log(f"[Esquemas] Disponíveis: {esquemas_validos}")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao buscar esquemas:\n{e}")
            self.log(f"[Erro] Falha ao buscar esquemas: {e}")

    def selecionar_geojson(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar GeoJSON", "", "GeoJSON (*.geojson)")
        if caminho:
            self.geojson_input.setText(caminho)
            self.aoi_info = {"geojson": caminho}
            self.log(f"[AOI] Selecionado: {self.aoi_info}")

    def listar_tabelas_do_esquema(self):
        esquema = self.schema_combo.currentText()
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT f_table_name 
                FROM geometry_columns 
                WHERE f_table_schema = %s;
            """, (esquema,))
            tabelas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            self.tabelas_com_geometria = tabelas
            self.executar_intersecoes_btn.setEnabled(True)
            self.log(f"[Tabelas] Esquema '{esquema}': {tabelas}")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao listar tabelas:\n{e}")
            self.log(f"[Erro] Falha ao listar tabelas: {e}")

    def executar_st_intersect(self):
        if not self.aoi_info.get("geojson"):
            QMessageBox.warning(self, "Erro", "Selecione uma AOI antes de executar.")
            return

        try:
            aoi = gpd.read_file(self.aoi_info["geojson"]).to_crs(epsg=4674)
            wkt = aoi.geometry.union_all().wkt
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler a AOI:\n{e}")
            self.log(f"[Erro] Falha ao ler AOI: {e}")
            return

        resultados = []
        ignoradas = []
        falhas = []
        esquema = self.schema_combo.currentText()

        for tabela in self.tabelas_com_geometria:
            try:
                query = f"""
                    SELECT COUNT(*) 
                    FROM "{esquema}"."{tabela}"
                    WHERE geom IS NOT NULL
                    AND ST_IsValid(geom)
                    AND ST_SRID(geom) = 4674
                    AND ST_Intersects(geom, ST_GeomFromText('{wkt}', 4674));
                """
                with self.conn.cursor() as cur:
                    cur.execute(query)
                    count = cur.fetchone()[0]

                    if count > 0:
                        # Coleta colunas e amostras
                        cur.execute(f"""SELECT * FROM "{esquema}"."{tabela}" LIMIT 5""")
                        colunas = [desc[0] for desc in cur.description if desc[0] != "geom"]
                        linhas = cur.fetchall()

                        resultados.append({
                            "tabela": tabela,
                            "count": count,
                            "colunas": colunas,
                            "linhas": linhas
                        })
                        self.log(f"[OK] {tabela} -> {count} feições intersectam")
                    else:
                        self.log(f"[Info] {tabela} -> 0 feições intersectam")

            except Exception as e:
                self.log(f"[Erro] ao processar {tabela}: {e}")
                falhas.append(tabela)

        if falhas:
            self.log(f"[Aviso] Tabelas com erro de interseção: {falhas}")
        if ignoradas:
            self.log(f"[Aviso] Tabelas ignoradas: {ignoradas}")

        # Salva para uso posterior
        self.resultados_intersecao = resultados

        # Gera visualização
        self.atualizar_arvore_resultados()

        self.tabs.setTabVisible(1, True)
        self.tabs.setCurrentIndex(1)
        self.diagnostico_btn.setEnabled(True)
        self.log(f"[Resumo] Total de camadas com interseção: {len(resultados)}")

    def atualizar_arvore_resultados(self):
        self.tree_resultados.clear()

        for r in self.resultados_intersecao:
            tabela = r['tabela']
            colunas = r['colunas']
            linhas = r['linhas']

            try:
                item = QTreeWidgetItem([tabela])
                item.setCheckState(0, Qt.CheckState.Checked)

                # Transforma linhas em dicionários para acesso por campo
                registros = [
                    {col: val for col, val in zip(colunas, linha)}
                    for linha in linhas
                ]

                for campo in colunas:
                    child = QTreeWidgetItem([f" {campo}"])
                    valores = []

                    for reg in registros:
                        val = reg.get(campo)
                        if val is not None and type(val) not in (dict, list):
                            val_str = str(val).strip()
                            if val_str and val_str not in valores:
                                valores.append(val_str)
                        if len(valores) >= 5:
                            break

                    for v in valores:
                        subitem = QTreeWidgetItem([f"  -> {v[:100]}"])
                        child.addChild(subitem)

                    item.addChild(child)

                self.tree_resultados.addTopLevelItem(item)

            except Exception as e:
                self.log(f"[ERRO] ao exibir {tabela}: {e}")


    def exportar_csv_diagnostico(self):
        if not hasattr(self, 'resultados_intersecao') or not self.resultados_intersecao:
            QMessageBox.warning(self, "Aviso", "Nenhum resultado disponível para exportar.")
            return

        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar Diagnóstico CSV", "", "CSV (*.csv)")
        if not caminho:
            return

        try:
            import pandas as pd
            dados = [
                {"Tabela": r["tabela"], "Feições Encontradas": r["count"]}
                for r in self.resultados_intersecao
            ]
            df = pd.DataFrame(dados)
            df.to_csv(caminho, index=False, encoding="utf-8-sig")
            QMessageBox.information(self, "Sucesso", "Diagnóstico exportado com sucesso!")
            self.log(f"[Export] Diagnóstico salvo em: {caminho}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar CSV:\n{e}")
            self.log(f"[Erro] Falha ao exportar CSV: {e}")


    def exportar_geopackage_final(self):
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar GeoPackage", "", "GeoPackage (*.gpkg)")
        if not caminho:
            return
        try:
            aoi = gpd.read_file(self.aoi_info["geojson"]).to_crs(epsg=4674)
            aoi.to_file(caminho, layer="AOI", driver="GPKG")
            esquema = self.schema_combo.currentText()
            cursor = self.conn.cursor()
            union_wkt = aoi.geometry.union_all().wkt
            for i in range(self.tree_resultados.topLevelItemCount()):
                item = self.tree_resultados.topLevelItem(i)
                if item.checkState(0) == Qt.CheckState.Checked:
                    tabela = item.text(0)
                    nome_geom = "geom"
                    if not nome_geom:
                        self.log(f"[Aviso] Tabela '{tabela}' ignorada na exportação (sem campo de geometria identificado).")
                        continue
                    query = f'''
                        SELECT * FROM "{esquema}"."{tabela}"
                        WHERE ST_Intersects("{nome_geom}", ST_GeomFromText(%s, 4674))
                    '''
                    cursor.execute(f'SELECT * FROM "{esquema}"."{tabela}" LIMIT 0')
                    colunas = [desc[0] for desc in cursor.description]
                    try:
                        gdf = gpd.read_postgis(query, self.conn, geom_col=nome_geom, params=[union_wkt])
                        if gdf.empty:
                            self.log(f"[Aviso] Tabela '{tabela}' não possui feições para exportar.")
                            continue
                        # Remove geometrias inválidas e vazias, mas aceita qualquer tipo
                        gdf = gdf[gdf.is_valid & ~gdf.is_empty]
                        if gdf.empty:
                            self.log(f"[Aviso] Tabela '{tabela}' só possui geometrias inválidas/vazias e foi ignorada.")
                            continue
                        # Se houver geometrias ZM, converte para Z (descarta M)
                        if any("ZM" in str(geom) for geom in gdf.geometry):
                            from shapely.geometry import mapping, shape
                            def remove_m(geom):
                                # Converte para dict, remove 'm', reconstrói
                                geom_dict = mapping(geom)
                                if "coordinates" in geom_dict:
                                    def strip_m(coords):
                                        # Remove M de cada coordenada
                                        if isinstance(coords[0], (float, int)):
                                            # É um ponto
                                            return coords[:3]
                                        return [strip_m(c) for c in coords]
                                    geom_dict["coordinates"] = strip_m(geom_dict["coordinates"])
                                return shape(geom_dict)
                            gdf["geometry"] = gdf["geometry"].apply(remove_m)
                            self.log(f"[Aviso] Geometrias ZM convertidas para Z na camada '{tabela}'.")
                        # Exporta sem transformar o tipo de geometria, aceita qualquer tipo (incluindo Z)
                        gdf.to_file(
                            caminho,
                            layer=tabela,
                            driver="GPKG",
                            encoding="utf-8",
                            geometry_type=None
                        )
                    except Exception as e:
                        self.log(f"[Erro] Falha ao exportar camada '{tabela}': {e}")
                        continue
            cursor.close()
            QMessageBox.information(self, "Sucesso", "GeoPackage exportado com sucesso!")
            self.log(f"[Export] GeoPackage salvo em: {caminho}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar GeoPackage:\n{e}")
            self.log(f"[Erro] Falha ao exportar GeoPackage: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    janela = AbaConexaoPostgre()
    janela.show()
    sys.exit(app.exec())
