#!/bin/bash

# Verifica se um diretório foi fornecido como argumento
if [ -z "$1" ]; then
  DIRECTORY="."
else
  DIRECTORY="$1"
fi

# Encontrar e adicionar arquivos menores que 50 MB ao git
find "$DIRECTORY" -type f -size -50M -print0 | xargs -0 git add --

