# VAD Framework

VAD (Vessel Activity Detection) Framework é um projeto desenvolvido para detectar e analisar atividades suspeitas de embarcações usando técnicas de fusão de dados e aprendizado de máquina.

## Funcionalidades

- Detecção de atividades suspeitas de embarcações
- Análise de trajetórias de navios
- Identificação de padrões de pesca ilegal
- Detecção de encontros entre embarcações
- Análise de comportamentos de loitering
- Detecção de atividades em áreas restritas

## Estrutura do Projeto

```
.
├── data/                  # Dados de entrada (shapefiles, datasets)
├── docs/                  # Documentação e referências
├── src/                   # Código fonte
│   ├── behaviours/       # Módulos de detecção de comportamentos
│   ├── database/         # Módulos de banco de dados
│   ├── rules/            # Regras e zonas de restrição
│   ├── tools/            # Ferramentas auxiliares
│   └── ui_expert/        # Interface para especialistas
├── templates/            # Templates HTML para visualização
└── requirements.txt      # Dependências do projeto
```

## Instalação

1. Clone o repositório:
```bash
git clone git@github.com:vindn/vad_framework.git
cd vad_framework
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Uso

O framework pode ser executado de diferentes formas:

1. Processamento em lote:
```bash
python main.py
```

2. Processamento em streaming:
```bash
python main_jdl_stream.py
```

3. Interface para especialistas:
```bash
python ui_expert/classifica_foto.py
```

## Arquivos Grandes

Alguns arquivos de dados e modelos são muito grandes para serem armazenados no GitHub. Estes arquivos devem ser baixados separadamente e colocados nos diretórios apropriados:

- `data/sintetic/gdf_sintetic.pkl`
- `data/sintetic/list_encounters_3meses.pickle`
- `data/sistram/gdf_*_*.pickle`
- `metamodel.db`

## Contribuição

Para contribuir com o projeto:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Crie um Pull Request

## Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
