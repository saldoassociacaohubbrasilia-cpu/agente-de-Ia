import { useEffect, useState } from 'react'
import { buscarPerfil } from './lib/api.js'
import Login from './paginas/Login.jsx'
import EsqueciSenha from './paginas/EsqueciSenha.jsx'
import RedefinirSenha from './paginas/RedefinirSenha.jsx'
import Conversa from './paginas/Conversa.jsx'
import './App.css'

const CHAVE_TOKEN = 'saldo_token'

// Sem router: o link de redefinição de senha do e-mail chega como
// ?token=... na raiz do site, o que funciona em qualquer hospedagem
// estática sem precisar configurar fallback de rota de SPA.
function lerTokenResetDaUrl() {
  return new URLSearchParams(window.location.search).get('token')
}

function App() {
  const [token, definirToken] = useState(() => localStorage.getItem(CHAVE_TOKEN))
  const [perfil, definirPerfil] = useState(null)
  const [verificandoSessao, definirVerificandoSessao] = useState(Boolean(token))
  const [erroConexao, definirErroConexao] = useState('')
  const [tentativa, definirTentativa] = useState(0)
  const [tokenReset, definirTokenReset] = useState(lerTokenResetDaUrl)
  const [mostrarEsqueciSenha, definirMostrarEsqueciSenha] = useState(false)

  useEffect(() => {
    if (!token) {
      definirVerificandoSessao(false)
      return
    }
    definirVerificandoSessao(true)
    definirErroConexao('')
    buscarPerfil(token)
      .then((dados) => definirPerfil(dados))
      .catch((erro) => {
        if (erro.status === 401) {
          localStorage.removeItem(CHAVE_TOKEN)
          definirToken(null)
        } else {
          // Sessão pode continuar válida — não desloga por causa de falha de
          // rede/servidor, só avisa e deixa a professora tentar de novo.
          definirErroConexao(erro.message)
        }
      })
      .finally(() => definirVerificandoSessao(false))
  }, [token, tentativa])

  function aoLogar(novoToken) {
    localStorage.setItem(CHAVE_TOKEN, novoToken)
    definirToken(novoToken)
  }

  function sair() {
    localStorage.removeItem(CHAVE_TOKEN)
    definirToken(null)
    definirPerfil(null)
  }

  function aoConcluirRedefinicao() {
    window.history.replaceState({}, '', window.location.pathname)
    definirTokenReset(null)
  }

  // Link de e-mail tem prioridade sobre qualquer outra tela, logada ou não.
  if (tokenReset) {
    return <RedefinirSenha token={tokenReset} aoConcluir={aoConcluirRedefinicao} />
  }

  if (verificandoSessao) {
    return (
      <div className="app-carregando" role="status">
        Carregando...
      </div>
    )
  }

  if (token && erroConexao) {
    return (
      <div className="app-erro-conexao" role="alert">
        <p>{erroConexao}</p>
        <button type="button" onClick={() => definirTentativa((n) => n + 1)}>
          Tentar de novo
        </button>
      </div>
    )
  }

  if (!token || !perfil) {
    if (mostrarEsqueciSenha) {
      return <EsqueciSenha aoVoltar={() => definirMostrarEsqueciSenha(false)} />
    }
    return <Login aoLogar={aoLogar} aoEsqueciSenha={() => definirMostrarEsqueciSenha(true)} />
  }

  return <Conversa token={token} perfil={perfil} aoSair={sair} />
}

export default App
