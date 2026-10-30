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

**[Descarregar 0.2.0-rc3 — versão experimental](https://github.com/Xcat2008/redmi-note12proplus-nas/releases/tag/v0.2.0-rc3).** Inclui imagem limpa, assistente Windows e um programa de descarga que verifica e junta as partes automaticamente.

A rc3 acrescenta codificação H.264 MediaTek no browser, mantém a composição Mali, recupera os núcleos disponíveis sem desativar proteções térmicas e corrige as páginas de abertura e as duas variantes UEFI do Proxmox. O teste da transmissão foi feito a 720p30; nem todas as etapas usam hardware. [Medições e limites](docs/SELKIES-MEDIATEK.md).

## Estado desta publicação

Esta é uma **versão experimental**, destinada apenas ao **Redmi Note 12 Pro+ 5G 22101316UG / rubypro / 256 GB**, com firmware **OS2.0.16.0.UMOEUXM**, slot **a**, e bootloader previamente desbloqueado pela Xiaomi. A instalação apaga o telefone e precisa de Internet no primeiro arranque. Não é um atualizador de uma NAS existente.

A rc2 passou a instalação física supervisionada. A rc3 mantém exatamente esse boot/layout e acrescenta userspace testado na NAS do projeto. Não foi repetida a instalação física completa da rc3 nem feito um teste num segundo aparelho. [Guia do assistente](docs/INSTALL-WIZARD.pt-PT.md) · [Âmbito da imagem](docs/IMAGE-INSTALLER.md).

A imagem é construída separadamente, sem redes, chaves privadas, sessões Steam, jogos, BIOS, filmes ou máquinas virtuais do autor. As fontes correspondentes a 1067 versões de componentes, licenças originais e SHA-256 acompanham a release.

Homeio, Jellyfin, RetroArch, Steam e Sunshine mantêm os perfis documentados. O Bluetooth pode ser gerido nas definições do Homeio; o comando Xbox foi testado no aparelho do projeto. A Steam abre em Big Picture com composição Mali; a compatibilidade de todos os seus jogos não está certificada. Hub, Ethernet e carregamento simultâneo foram exercitados; discos externos dependem da ligação, do adaptador e do disco.

O Proxmox ARM64 vem como base limpa opcional e desligada, com preparação nas definições do Homeio. Só pode ser ativado com EL2/KVM realmente disponível. Desbloquear o bootloader não garante EL2, e a rc3 não o ativa automaticamente num aparelho de origem. A NAS funciona sem Proxmox. Memória extra em disco, cuidados opcionais de bateria e cópias pessoais automáticas começam desligados.

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

Antes de associar apoios à distribuição, consulta a [revisão de licenças e distribuição](docs/DISTRIBUTION-REVIEW.pt-PT.md): a rc3 inclui um núcleo com restrições comerciais, que a licença do projeto não substitui. O [guia EL2/KVM](docs/KVM-ACTIVATION.pt-PT.md) explica também a etapa de ativação ainda por concluir para aparelhos de origem.

O trabalho usa software criado por várias comunidades. Os agradecimentos e respetivos links estão em [CREDITS.md](CREDITS.md), em especial **Droidian, Debian, Halium, libhybris, Linux e Homeio**. A autoria deste projeto é a integração e adaptação feita por José Miranda; não é a autoria desses sistemas.

[Documentação principal em inglês](README.md) · [Licenças](LICENSE.md)
