Hoje dei um passo importante na evolução do WhatYouSaid, meu projeto de extração e enriquecimento de metadados de vídeos
do YouTube.

Nesta atualização, refatorei completamente o extrator de YouTube, começando pela definição de uma interface clara (
IYoutubeExtractor) que separa o contrato da implementação e abre espaço para novos provedores no futuro.

Também criei um YoutubeMetadataDTO com Pydantic para representar os metadados do vídeo de forma tipada e validada,
incluindo campos como título, duração, categorias, tags, canal, uploader e URLs. Isso torna o pipeline muito mais
previsível e fácil de integrar com outras partes do sistema.

O extrator agora usa yt_dlp para coletar os metadados e youtube_transcript_api para buscar a transcrição, com tratamento
explícito para casos como vídeos sem transcript ou com transcripts desativadas. Em paralelo, integrei tudo com um logger
próprio, registrando contexto rico (ID do vídeo, idioma, tamanho da transcrição) para facilitar monitoramento e
troubleshooting em produção.

Para fechar, ampliei a cobertura de testes, garantindo que o fluxo de extração e o comportamento do logger se mantenham
estáveis conforme o projeto cresce. Esse refactor deixa a base muito mais preparada para as próximas funcionalidades de
enriquecimento e análise de conteúdo em cima dos vídeos.

O código está disponível aqui: https://github.com/ericksonlopes/WhatYouSaid/pull/17


