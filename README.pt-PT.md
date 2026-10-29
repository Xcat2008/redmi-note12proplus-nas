![Redmi NAS — José Miranda](docs/assets/redmi-nas-hero.png)

*Ilustração de capa do projeto. As capturas abaixo mostram o aparelho real em funcionamento.*

# NAS num Redmi Note 12 Pro+ 5G

🇵🇹 **Projeto português, desenvolvido em Portugal por José Miranda (Xcat2008).**

Transformar um telemóvel antigo num servidor doméstico: **Droidian / Debian nativo**, Wi-Fi, armazenamento interno e **Homeio** como ambiente de trabalho acessível pelo browser. O Homeio funciona em segundo plano; o ecrã do telefone pode ficar apagado sem parar a NAS.

![Arquitetura](docs/assets/architecture.svg)

## O painel a funcionar no Redmi

Capturas reais do Homeio, feitas em 26 de outubro de 2026. O servidor está no telemóvel, com Linux nativo e ligação por Wi-Fi.

![Homeio em funcionamento no Redmi NAS](docs/screenshots/homeio-live-desktop.png)

| Processador: oito núcleos | GPU integrada |
| --- | --- |
| ![Seis Cortex-A55 e dois Cortex-A78](docs/screenshots/homeio-cpu.png) | ![ARM Mali-G68 MC4](docs/screenshots/homeio-gpu.png) |

<details>
<summary>Memória e notas das capturas</summary>

![Memória reconhecida pelo Linux](docs/screenshots/homeio-memory.png)

O aparelho tem 8 GiB de RAM física; o Linux apresenta cerca de 7,4 GiB após as reservas da plataforma. Os valores de utilização variam. A descodificação e a codificação de vídeo MediaTek, com redimensionamento na gráfica Mali, já foram testadas no leitor web do Jellyfin. Os identificadores da rede foram ocultados e o atalho do Jellyfin foi retirado apenas das capturas. [Notas das imagens](docs/SCREENSHOTS.md).

</details>

## Melhorias recentes

A atualização de código acrescenta apresentação Vulkan na Mali, distribuição da emulação pelos núcleos rápidos, redução de imagens repetidas e correções de estabilidade do kernel e do arranque. As [notas técnicas de desempenho e estabilidade](docs/PERFORMANCE.md) documentam as medições e os limites de temperatura, sem overclock. Estas alterações ainda não constituem uma nova imagem limpa pronta a instalar.

## Proxmox e máquinas virtuais

O Redmi do projeto já tem **Proxmox VE 9.2.20 ARM64 com aceleração KVM**. Foi testada uma VM Debian 13 com oito CPUs virtuais, com cálculo real nos oito núcleos físicos, persistência no disco, rede, consola web e reinício. A adaptação do QEMU resolve a inconsistência de cache entre os A55 e os A78 neste kernel.

As [instruções e o estado dos testes](docs/PROXMOX.md) e o [código das correções](apps/proxmox/README.md) estão publicados. É um perfil experimental e opcional: a rc7 não o inclui; a candidata 0.2 em preparação acrescenta a base Proxmox limpa, desligada, e o kernel/módulos KVM correspondentes. A reinstalação limpa supervisionada da rc2, o arranque automático da NAS, a ativação opcional do Proxmox, uma VM de oito CPUs e o reinício completo já passaram no telefone do projeto. A ativação EL2 num aparelho de origem continua por automatizar e validar.

O [guia do assistente Windows](docs/INSTALL-WIZARD.pt-PT.md) explica o fluxo de descarga, verificação e configuração. O instalador gráfico mantém a instalação bloqueada nas candidatas não aprovadas. O primeiro arranque precisa de Internet para obter os programas de origem.

## Estado desta publicação

Esta é uma **prévia técnica com código-fonte, configurações e notas de instalação**. A NAS funciona no aparelho do projeto. Também foi construída uma imagem limpa de arranque e dados, com um instalador para Windows, e a rc2 já passou a reinstalação supervisionada no telefone do projeto, sem reparações na configuração da NAS. Falta concluir a revisão de distribuição dos binários e a ativação EL2 de origem antes de anunciar uma solução pública completa. Consulta o [estado do instalador](docs/IMAGE-INSTALLER.md).

O aparelho usado é o **Redmi Note 12 Pro+ 5G, modelo 22101316UG (rubypro)**, com Dimensity 1080, 8 GiB de RAM física e 256 GB de armazenamento. Não usar imagens do modelo 4G ou de outro telemóvel.

Confirmámos Linux nativo, Wi-Fi, Homeio, Docker ARM64, arranque automático e funcionamento da NAS com o ecrã apagado. O Jellyfin reproduz no browser e converte 1080p para 720p usando descodificação MediaTek, redimensionamento Mali e codificação H.264 MediaTek. O Bluetooth pode ser gerido em **Settings → Bluetooth**, no Homeio: ligar/desligar, procurar, emparelhar, ligar, desligar e esquecer dispositivos. A pesquisa e os controlos do rádio foram testados no browser; o emparelhamento e os botões de um comando Xbox também foram confirmados no aparelho do projeto. [Como usar](docs/BLUETOOTH.md). Hub, carregamento simultâneo com USB e discos externos ainda não foram ensaiados; SIM e câmaras não estão validados.

A Steam usa o cliente ARM64 oficial e abre em Big Picture, com composição pela Mali e um atalho separado do RetroArch no Homeio e no Moonlight. As correções de arranque, atualização e recuperação fazem parte do perfil de instalação. O reinício completo da NAS voltou a passar em 28 de outubro de 2026. A compatibilidade de todos os jogos da Steam não está certificada. [Perfil nativo e validação](docs/NATIVE-GAMING.md).

## Vídeo por hardware

Os perfis de energia estão em **Settings → Performance**: Poupança, Equilibrado e Desempenho. O modo recomendado é **Equilibrado**, com frequência ajustada à carga. Foi corrigido o gestor que voltava a limitar o CPU; os testes confirmaram os limites de fábrica do processador, a subida automática da Mali e a resposta do controlador de memória. Os perfis mantêm as frequências de fábrica e o controlo automático das tensões. [Detalhes e medições](docs/ENERGY.md).

![Percurso do vídeo no MediaTek](docs/assets/mediatek-video.svg)

A ponte de vídeo utiliza os serviços multimédia do Android que o Droidian já inclui. Foram testados H.264, HEVC e VP9 SDR, saída H.264, reprodução no browser e procura dentro do filme. O áudio, o empacotamento HLS e outros serviços continuam a usar CPU. HDR, legendas gravadas na imagem e outros formatos não ficam certificados por estes testes. Esta integração também não acelera automaticamente todas as aplicações.

A imagem limpa candidata já inclui o adaptador compilado, o código e o perfil automático do Jellyfin. A rc2 já passou a instalação de raiz supervisionada e o arranque automático da NAS no telefone do projeto. [Detalhes e testes](docs/MEDIATEK-VIDEO.md).

## Como começar

1. Começar pelo [guia rápido](docs/QUICKSTART.md) e ler o [guia de instalação e recuperação](docs/INSTALLATION.md).
2. Confirmar a [compatibilidade do hardware](docs/COMPATIBILITY.md).
3. Consultar as [fontes e versões](sources.lock.json).
4. Depois de o Linux arrancar, aplicar as adaptações de energia, ecrã e Homeio.
5. Fazer os [testes de validação](docs/VALIDATION.md), incluindo ecrã apagado e reinício.

O desbloqueio do bootloader foi feito através do processo oficial da Xiaomi. Esse desbloqueio apaga os dados. A preparação do armazenamento Linux também exige apagar a partição de dados; a cópia de segurança e um plano de recuperação devem estar prontos antes de alterar o aparelho.

A caixa 3D é um projeto pessoal separado e não faz parte deste repositório. Também não são publicados dados pessoais, palavras-passe, chaves SSH, firmware proprietário ou uma cópia do sistema já configurado.

## Donativos e agradecimentos

O perfil GitHub Sponsors do autor aguarda aprovação. O link de apoio será acrescentado quando estiver ativo.

O trabalho usa software criado por várias comunidades. Os agradecimentos e respetivos links estão em [CREDITS.md](CREDITS.md), em especial **Droidian, Debian, Halium, libhybris, Linux e Homeio**. A autoria deste projeto é a integração e adaptação feita por José Miranda; não é a autoria desses sistemas.

[Documentação principal em inglês](README.md) · [Licenças](LICENSE.md)
