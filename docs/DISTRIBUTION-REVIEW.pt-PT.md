# Revisão de distribuição, licenças e privacidade

Revisão técnica de 30 de outubro de 2026. Não é uma certificação de ausência de responsabilidade jurídica. O objetivo é documentar os componentes efetivamente distribuídos, corrigir atribuições e não apresentar etapas experimentais como concluídas.

## Resultados e medidas

| Área | Verificação | Resultado e medida |
| --- | --- | --- |
| Autoria | Licença, créditos e avisos por ficheiro | A integração original é de José Miranda (Xcat2008), Portugal. Homeio, Droidian, kernel, emuladores e restantes projetos mantêm autoria e licenças próprias. Não se reivindica exclusividade histórica sobre a ideia. |
| Fontes da rc3 | Inventário de pacotes e partes de fontes da release | O inventário técnico cobre as 1067 versões de pacotes instaladas; também foram reunidas as fontes fixadas dos componentes nativos e do kernel. O inventário não substitui as condições específicas de cada licença. |
| Licença geral | `LICENSE.md` e cabeçalhos individuais | Clarificadas as exceções GPL, MIT, Bluetooth e os componentes não comerciais. A licença AGPL da integração não altera as licenças das dependências. |
| Homeio modificado | Oferta de código-fonte na interface | Acrescentados ao código um link nas definições e um exportador das fontes efetivamente instaladas. O exportador usa caminhos explícitos, exclui `.env`, bases de dados e dados de execução e rejeita symlinks. Esta alteração destina-se às próximas instalações; não consta automaticamente do binário rc3 já publicado. |
| Dados pessoais | Construção da imagem e âmbito dos pacotes | A rc3 foi construída a partir de base limpa, com credenciais individuais na instalação. Não é uma clonagem da NAS pessoal. Jogos, BIOS, ficheiros multimédia, contas, sessões e chaves do autor não fazem parte do pacote. Capturas públicas também não devem mostrar bibliotecas pessoais. |
| Firmware proprietário | Conteúdo e requisitos do instalador | O projeto não fornece a ROM de fábrica, preloader ou bibliotecas proprietárias extraídas do telefone do autor. O proprietário deve obter e conservar o firmware correspondente ao seu aparelho. Os restantes pacotes mantêm os avisos e requisitos de redistribuição próprios. |
| EL2/KVM | Diferença entre instalação limpa e ativação da plataforma | A NAS não altera GPT para ativar EL2. O método experimental do aparelho do projeto não está apresentado como ativador público validado. A avaliação jurídica da distribuição de uma ferramenta que afete o arranque permanece separada da validação técnica. |

## Genesis Plus GX e apoios ao projeto

A rc3 contém Genesis Plus GX na revisão `60bee4c724859710ce05672239e5b601ad01382e`. A [licença exata](https://raw.githubusercontent.com/libretro/Genesis-Plus-GX/60bee4c724859710ce05672239e5b601ad01382e/LICENSE.txt) restringe a venda e o uso em produtos ou atividades comerciais e exige preservar avisos e, nas redistribuições modificadas, as fontes correspondentes. A release inclui esses avisos e as fontes; o núcleo não deve ser descrito como GPL.

O apoio voluntário ao trabalho original não dá autorização para ignorar essa restrição. Esta revisão **não determina que qualquer donativo seja automaticamente proibido**, nem conclui que associar financiamento ao pacote seja permitido em todas as circunstâncias. Antes de ativar uma campanha associada à distribuição, esclarecer esse âmbito com os titulares ou separar uma futura distribuição sem esse núcleo. Não foi ativado um link de donativos durante esta revisão. O núcleo da instalação privada não foi removido.

A possibilidade de vender software livre sob GPL não elimina as condições de outras licenças presentes no mesmo pacote. A [explicação da GNU](https://www.gnu.org/philosophy/selling.en.html) aplica-se ao software coberto pelas suas condições, não converte dependências não comerciais em software comercialmente redistribuível.

## Código-fonte e avisos

Mantêm-se os avisos em `THIRD_PARTY_NOTICES.md`, `CREDITS.md`, `LICENSES/` e nos próprios ficheiros. As fontes da versão distribuída devem permanecer acessíveis com o pacote. Alterações posteriores no ramo principal não substituem as fontes exatas de uma release anterior.

A AGPL contém uma obrigação específica de oferta de fontes para utilizadores que interagem pela rede com uma versão modificada; ver a [secção 13 da licença](../LICENSES/AGPL-3.0-only.txt). O exportador e o link local acrescentados para o Homeio atendem a esse caso. Uma atualização da aplicação exige regenerar o arquivo a partir da versão realmente servida. Não incluir configuração privada nesse arquivo.

Os recursos ARMSX2 incluem fontes Roboto: os avisos Apache estão nas fontes correspondentes e nos avisos de pacotes disponibilizados. Não se deve interpretar a ausência de um aviso ao lado de cada recurso como prova de que o aviso está ausente de toda a distribuição. Uma auditoria de futuras versões deve repetir a conferência sobre os ficheiros efetivos.

## Limites jurídicos do arranque e da interoperabilidade

O [Decreto-Lei n.º 252/94, texto consolidado](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1994-34555675), reconhece direitos do utilizador legítimo e estabelece condições para descompilação necessária à interoperabilidade. Também contém disposições sobre mecanismos destinados à neutralização não autorizada de salvaguardas de programas. Não se pode concluir apenas da propriedade do telefone que qualquer ferramenta de alteração do arranque pode ser distribuída sem restrições.

Isso também não demonstra que uma alteração de configuração de arranque seja, por si só, ilícita. A finalidade, o funcionamento, o software afetado, as autorizações e a forma de distribuição precisam de avaliação concreta. Para segurança jurídica sobre a publicação de um ativador EL2, a conclusão teria de ser dada por um jurista com esses elementos, não por uma promessa de conformidade absoluta neste README. A NAS e os componentes opcionais continuam a ser documentados com o seu estado real.

Esta revisão não valida usos de obras de terceiros, contas ou conteúdos obtidos por utilizadores. O projeto público fornece integração e fontes, não jogos, BIOS ou formas de obter conteúdos protegidos.
