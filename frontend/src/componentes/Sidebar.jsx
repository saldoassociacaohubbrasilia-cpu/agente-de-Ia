function Sidebar({ perfil, conversas, conversaAtualId, aoSelecionar, aoIniciarNova, aoSair }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-professor">
        <p className="sidebar-nome">{perfil.nome_completo}</p>
        {perfil.escola && <p className="sidebar-escola">{perfil.escola}</p>}
      </div>

      <button type="button" className="sidebar-nova-conversa" onClick={aoIniciarNova}>
        + Nova conversa
      </button>

      <nav className="sidebar-lista" aria-label="Histórico de conversas">
        {conversas.length === 0 && <p className="sidebar-vazio">Nenhuma conversa ainda.</p>}
        <ul>
          {conversas.map((conversa) => (
            <li key={conversa.id}>
              <button
                type="button"
                className={conversa.id === conversaAtualId ? 'sidebar-item sidebar-item-ativo' : 'sidebar-item'}
                onClick={() => aoSelecionar(conversa.id)}
                aria-current={conversa.id === conversaAtualId}
              >
                {conversa.titulo}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <button type="button" className="sidebar-sair" onClick={aoSair}>
        Sair
      </button>
    </aside>
  )
}

export default Sidebar
