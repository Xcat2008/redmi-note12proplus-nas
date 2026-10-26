![Redmi NAS — José Miranda](docs/assets/banner.svg)

# NAS num Redmi Note 12 Pro+ 5G

🇵🇹 **Projeto português, desenvolvido em Portugal por José Miranda (Xcat2008).**

Projeto de **José Miranda (Xcat2008)**, [Xcat2008](https://github.com/Xcat2008).

Transformar um telemóvel antigo num servidor doméstico: **Droidian / Debian nativo**, Wi-Fi, armazenamento interno e **Homeio** como ambiente de trabalho acessível pelo browser. O Homeio funciona em segundo plano; o ecrã do telefone pode ficar apagado sem parar a NAS.

![Arquitetura](docs/assets/architecture.svg)

## Estado desta publicação

Esta é uma **prévia técnica com código-fonte, configurações e notas de instalação**. A configuração da NAS já tem um ponto de entrada automatizado para um Droidian nativo que arranque; substituir Android por Linux ainda exige o processo manual de adaptação. Não inclui uma imagem universal. A instalação original funcionou neste Redmi; ainda falta repetir o procedimento público num segundo aparelho limpo.

O aparelho usado é o **Redmi Note 12 Pro+ 5G, modelo 22101316UG (rubypro)**, com Dimensity 1080, 8 GiB de RAM física e 256 GB de armazenamento. Não usar imagens do modelo 4G ou de outro telemóvel.

Confirmámos Linux nativo, Wi-Fi, Homeio, Docker ARM64, arranque automático e funcionamento da NAS com o ecrã apagado. O Jellyfin também abre pela rede, depois de adaptar o modelo da loja que exigia dispositivos de vídeo do Raspberry Pi. A reprodução de filmes ainda precisa de teste. Hub, carregamento simultâneo com USB e discos externos ainda não foram ensaiados; SIM, Bluetooth e câmaras não estão validados.

## Como começar

1. Começar pelo [guia rápido](docs/QUICKSTART.md) e ler o [guia de instalação e recuperação](docs/INSTALLATION.md).
2. Confirmar a [compatibilidade do hardware](docs/COMPATIBILITY.md).
3. Consultar as [fontes e versões](sources.lock.json).
4. Depois de o Linux arrancar, aplicar as adaptações de energia, ecrã e Homeio.
5. Fazer os [testes de validação](docs/VALIDATION.md), incluindo ecrã apagado e reinício.

O desbloqueio do bootloader foi feito através do processo oficial da Xiaomi. Esse desbloqueio apaga os dados. A preparação do armazenamento Linux também exige apagar a partição de dados; a cópia de segurança e um plano de recuperação devem estar prontos antes de alterar o aparelho.

A caixa 3D é um projeto pessoal separado e não faz parte deste repositório. Também não são publicados dados pessoais, palavras-passe, chaves SSH, firmware proprietário ou uma cópia do sistema já configurado.

## Donativos e agradecimentos

O link de apoio financeiro está temporariamente desativado enquanto o autor confirma a configuração do pagamento.

O trabalho usa software criado por várias comunidades. Os agradecimentos e respetivos links estão em [CREDITS.md](CREDITS.md), em especial **Droidian, Debian, Halium, libhybris, Linux e Homeio**. A autoria deste projeto é a integração e adaptação feita por José Miranda; não é a autoria desses sistemas. Também não afirmamos que este seja o primeiro projeto deste género no mundo.

[Documentação principal em inglês](README.md) · [Licenças](LICENSE.md)
