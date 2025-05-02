Nível 0 - Pré-processamento:
Implementação: Neste estágio, você pode escrever código para limpar e normalizar os dados. Isso pode incluir a remoção de outliers, a padronização de formatos e a interpolação de dados faltantes. Ferramentas como pandas em Python são úteis para manipulação de dados.

Nível 1 - Fusão de Dados de Nível de Objeto:
Implementação: Aqui, você pode desenvolver algoritmos para combinar dados de diferentes fontes sobre um mesmo objeto ou evento. Isso pode envolver técnicas de correspondência de dados, como algoritmos de associação ou rastreamento. Bibliotecas como OpenCV para processamento de imagens ou ferramentas específicas de fusão de dados podem ser úteis.

Nível 2 - Fusão de Dados em Nível de Situação:
Implementação: Este nível exige uma análise mais complexa, como reconhecimento de padrões ou aprendizado de máquina, para interpretar o cenário global a partir dos dados. Você pode usar bibliotecas de aprendizado de máquina como scikit-learn ou TensorFlow para modelar e interpretar essas situações.

Nível 3 - Fusão de Dados em Nível de Impacto:
Implementação: Aqui, você foca na previsão e na avaliação de consequências futuras. Isso pode envolver a implementação de modelos preditivos ou de simulação. Técnicas de análise preditiva e modelagem de cenários são essenciais neste nível.

Nível 4 - Processo de Apoio à Decisão:
Implementação: Neste estágio final, você integra as informações obtidas dos níveis anteriores para apoiar a tomada de decisões. Isso pode envolver a criação de dashboards, relatórios automatizados ou sistemas de alerta. Ferramentas como Tableau para visualização de dados ou sistemas de relatórios automatizados podem ser incorporados.


vessel_activity_jdl/
│
├── data/                           # Dados brutos e processados
├── docs/                           # Documentação
├── tests/                          # Testes automatizados e testes de validacao
├── src/                            # Código fonte
│   ├── preprocessing.py            # (Nivel 0) Encapsula funcionalidades de limpeza, normalização e preparação dos dados.
|   ├── fusion_base.py              # Uma classe abstrata ou base que define a interface comum e/ou funcionalidades compartilhadas por todas as classes de fusão de dados.
│   ├── object_level_fusion.py      # (Nivel 1) Lida com a correlação e combinação de dados de diferentes fontes para cada objeto (embarcação).
│   ├── situational_awareness.py    # (Nivel 2) Realiza análises para entender o contexto ou situação geral, como padrões de movimento. Fusão dos dados dos meta modelos. Inferir dados no meta modelo
│   ├── impact_assessment.py        # (Nivel 3) Fusão de dados em nível de impacto. Foca na interpretação dos dados para previsão e avaliação de consequências futuras. Active learning para atualizar o metamodelo. Treinar metamodelo, coletar respostas do especialista.
│   └── decision_support.py         # (Nivel 4) Utiliza as informações processadas para fornecer insights e apoiar decisões, como a geração de alertas ou relatórios. Avaliação e resposta do especialista com relação a predição do modelo.
├── notebooks/                      # Jupyter notebooks para análises exploratórias
├── requirements.txt                # Dependências
└── main.py       
