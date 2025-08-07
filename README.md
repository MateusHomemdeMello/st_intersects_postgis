![Logo](https://img.shields.io/badge/PyQt6-GIS-blue)  
**Versão:** 1.0  
**Licença:** MIT  
**Autor:** *Mateus Homem de Mello*

---

## 📌 Descrição

Trata-se de uma aplicação desktop com interface gráfica desenvolvida em **Python** e **PyQt6** que realiza diagnósticos espaciais a partir de uma **área de interesse (AOI)**, consultando dinamicamente um banco de dados **PostgreSQL/PostGIS**.

O programa permite ao usuário:
- Importar credenciais do banco via arquivo JSON.
- Selecionar uma **AOI em formato GeoJSON**.
- Listar automaticamente todas as camadas geográficas de um esquema selecionado.
- Executar interseções espaciais entre a AOI e as camadas do banco.
- Visualizar os campos e valores identificados nas camadas intersectadas.
- Exportar os resultados como:
  - **Diagnóstico resumido em CSV**
  - **GeoPackage (GPKG)** com as feições que interceptam a AOI.

---

## 📂 Formatos de Entrada

| Tipo de dado | Formato | Observações |
|--------------|---------|-------------|
| AOI (Área de Interesse) | `.geojson` | Deve conter geometrias poligonais válidas |
| Credenciais de banco | `.json` | Deve conter os campos `host`, `port`, `dbname`, `user`, `password` |
| Base espacial | PostgreSQL com extensão PostGIS | As geometrias devem estar no SRID 4674 |

---

## 📍 Projeção Cartográfica

- **Sistema de Referência Espacial Obrigatório:** `EPSG:4674` (SIRGAS 2000)
- A AOI é automaticamente reprojetada para `EPSG:4674`, caso esteja em outro sistema.
- Todas as consultas SQL usam geometrias no SRID 4674.
- Camadas do GeoPackage exportado são salvas neste mesmo SRID.

---

## 📤 Produtos Gerados

| Produto | Formato | Descrição |
|---------|---------|-----------|
| Diagnóstico | `.csv` | Lista de camadas com número de feições que interceptam a AOI |
| Conjunto vetorial | `.gpkg` | GeoPackage com: camada da AOI e camadas do banco com interseção espacial |

---

## 🖥️ Interface

- Desenvolvida com **PyQt6** e tema escuro embutido.
- Possui duas abas:
  - **Entrada:** configurações de conexão, escolha de AOI e execução do diagnóstico.
  - **Visualização:** resultado da interseção com campos e valores exemplo, exportações.

---

## 🚀 Como Executar

1. Instale os requisitos:
   ```bash
   pip install PyQt6 geopandas psycopg2 shapely pandas
   ```

2. Execute o script:
   ```bash
   python nome_do_script.py
   ```

3. Preencha ou importe as credenciais do banco.

4. Escolha a **AOI (GeoJSON)**.

5. Selecione o esquema desejado e clique em:
   - `Buscar Tabelas`
   - `Executar Interseção`

6. Exporte os dados em `.csv` ou `.gpkg` na aba **Visualização**.

---

## 🧪 Exemplo de arquivo `credenciais.json`

```json
{
  "host": "localhost",
  "port": 5432,
  "dbname": "meu_banco",
  "user": "usuario",
  "password": "senha"
}
```

---

## ❗ Requisitos e Cuidados

- O banco de dados **deve conter colunas geométricas válidas** (tipo `geometry`) com SRID 4674.
- As tabelas precisam estar registradas na view `geometry_columns`.
- A AOI deve conter geometrias válidas e não nulas.
- Geometrias com dimensões **ZM** são automaticamente convertidas para **Z**.

---

## 📦 Estrutura dos Outputs

O GeoPackage exportado contém:
- Uma camada chamada `AOI` com a geometria da área de interesse.
- Camadas adicionais correspondentes às tabelas selecionadas, contendo **apenas feições que intersectam a AOI**.

---

## 📌 Licença

Este projeto está licenciado sob os termos da licença MIT.
