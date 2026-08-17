function Mensagem({ mensagem }) {
  const doAgente = mensagem.autor === 'agente'

  return (
    <div className={doAgente ? 'mensagem mensagem-agente' : 'mensagem mensagem-professor'}>
      {doAgente && (
        <span className="mensagem-avatar" aria-hidden="true">
          +
        </span>
      )}
      <div className="mensagem-corpo">
        <p className="mensagem-texto">{mensagem.texto}</p>

        {mensagem.fontes && mensagem.fontes.length > 0 && (
          <ul className="mensagem-fontes">
            {mensagem.fontes.map((fonte, indice) => (
              <li key={indice}>
                {fonte.arquivo}
                {fonte.pagina !== null && fonte.pagina !== undefined ? `, p. ${fonte.pagina}` : ''}
              </li>
            ))}
          </ul>
        )}

        {mensagem.chamado_id && (
          <p className="mensagem-chamado">Chamado #{mensagem.chamado_id} aberto com a equipe de suporte.</p>
        )}
      </div>
    </div>
  )
}

export default Mensagem
