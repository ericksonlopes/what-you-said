import os
import subprocess
import platform
from pathlib import Path
from dotenv import load_dotenv

# 1️⃣ Carregar variáveis do .env
load_dotenv()
token = os.getenv("SONAR_TOKEN")

if not token:
    print("❌ SONAR_TOKEN não encontrado. Configure no arquivo .env.")
    exit(1)

# 2️⃣ Detectar sistema operacional
system = platform.system().lower()
if system in ["windows", "darwin"]:  # Mac ou Windows
    sonar_host = "http://host.docker.internal:9000"
else:  # Linux
    sonar_host = "http://localhost:9000"

# 3️⃣ Configurações do projeto
project_key = "api"
project_name = "api"

# 4️⃣ Garantir que o arquivo sonar-project.properties exista
properties_path = Path("sonar-project.properties")
if not properties_path.exists():
    print("📄 Criando arquivo sonar-project.properties...")
    properties_content = f"""sonar.projectKey={project_key}
sonar.projectName={project_name}
sonar.language=py
sonar.sourceEncoding=UTF-8
sonar.sources=.
    """
    properties_path.write_text(properties_content)
    print("✅ Arquivo sonar-project.properties criado com sucesso.")

# 5️⃣ Montar comando Docker
cmd = [
    "docker", "run", "--rm",
    "-e", f"SONAR_HOST_URL={sonar_host}",
    "-v", f"{Path.cwd()}:/usr/src",
]

if system == "linux":
    cmd.append("--network=host")

cmd += [
    "sonarsource/sonar-scanner-cli",
    f"-Dsonar.projectKey={project_key}",
    "-Dsonar.sources=.",
    f"-Dsonar.host.url={sonar_host}",
    f"-Dsonar.login={token}",
    "-Dsonar.python.version=3.10",
]

# 6️⃣ Mostrar comando
print("\n▶️ Executando scanner com o comando:")
print(" ".join(cmd))
print("")

# 7️⃣ Executar o scanner
try:
    subprocess.run(cmd, check=True)
    print("\n✅ Scanner concluído com sucesso.")
except subprocess.CalledProcessError as e:
    print(f"\n❌ Falha ao executar o scanner (código {e.returncode})")