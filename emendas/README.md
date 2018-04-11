## Análise de emendas parlamentares da CLDF.

Este diretorio usa pipenv. Para baixar e instalar as dependencias, execute:

    pipenv install --skip-lock

Sem `--skip-lock` deveria funcionar, mas está travando.

Para rodar um índice local, execute:

    docker-compose up

Então um índice local estará disponível em `http://localhost:9200/` e um Kibana em `http://localhost:9200/_plugin/kibana`.

O código que extrai e massageia os dados está em `indexer.py`. Ele assume que há arquivos CSV no diretório `files/`, um por ano (`files/2018.csv`, `files/2017.csv`, etc).
