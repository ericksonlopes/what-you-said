# Execução do Scanner do SonarQube para Análise de Código (Python)

## 🧩 Requisitos

* **Docker** instalado
* **Python 3.9+** instalado
* Dependência `python-dotenv` instalada:

  ```bash
  pip install python-dotenv
  ```
* Variável de ambiente `SONAR_TOKEN` configurada (token gerado no SonarQube)

---

## ⚙️ Configuração do SonarQube

1. Suba os containers do **SonarQube** e do **PostgreSQL**:

   ```bash
   cd .sonarqube
   docker compose up -d
   ```

2. Acesse o painel do SonarQube em [http://localhost:9000](http://localhost:9000)

   Login padrão:

   * **Usuário:** `admin`
   * **Senha:** `admin`

3. Crie uma nova senha quando solicitado.

4. Crie um projeto manualmente:

   * Clique em **"Create Project > Manually"**
   * Nomeie o projeto (ex: `python_project`) e clique em **Set Up**
   * Escolha **Locally**
   * Gere um **token** e adicione no arquivo `.env` na raiz do projeto:

     ```env
     SONAR_TOKEN=seu-token-gerado
     ```

---

## ⚙️ (Opcional) Geração automática do `sonar-project.properties`

Se o projeto ainda **não possui** o arquivo `sonar-project.properties`, o script `scanner.py` pode criá-lo automaticamente com configurações básicas.

O arquivo gerado será semelhante a:

```
sonar.projectKey=python_project
sonar.projectName=python_project
sonar.language=py
sonar.sourceEncoding=UTF-8
sonar.sources=.
```

Isso evita a necessidade de criar o projeto manualmente antes da primeira execução.
O nome do projeto (`sonar.projectKey`) pode ser configurado dentro do próprio script `scanner.py`.

---

## 🧠 Integração com SonarLint

No **Visual Studio Code**, instale a extensão **SonarQube Setup** e configure a conexão com o servidor:

1. Vá em **SonarQube Setup → Add Sonar Server**
2. Preencha:

   * **Server URL:** `http://localhost:9000`
3. Clique em **Generate Token**
4. Após abrir o navegador e autorizar, clique em **Save connection**
5. Associe o projeto manualmente se necessário (ícone de **+** → selecione o projeto)

---

## 🚀 Rodando o Scanner

Na raiz do projeto, execute:

```bash
python .sonarqube/scanner.py
```

O script fará:

1. Leitura do token do `.env`
2. Geração automática do `sonar-project.properties` (se não existir)
3. Execução do **Sonar Scanner** dentro de um container Docker
4. Envio dos resultados de análise para o SonarQube

---

## ⚠️ Observações sobre Rede Docker

* **Linux:** usa automaticamente `--network=host`
* **Windows / Mac:** usa `http://host.docker.internal:9000`
  (ajuste tratado automaticamente no script)

---

## 🧹 Finalizando

Para parar o SonarQube e o PostgreSQL:

```bash
cd .sonarqube
docker compose down
```

---

## 📁 Estrutura esperada

```
project/
├── .sonarqube/
│   ├── compose.yaml
│   └── ...
├── .env
├── scanner.py
└── (seu código Python)
```
