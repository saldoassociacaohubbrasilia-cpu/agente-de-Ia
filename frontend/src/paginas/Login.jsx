import { useState } from 'react'
import { login } from '../lib/api.js'
import BarraMais from '../componentes/BarraMais.jsx'
import './Login.css'

function Login({ aoLogar, aoEsqueciSenha }) {
  const [usuario, definirUsuario] = useState('')
  const [senha, definirSenha] = useState('')
  const [enviando, definirEnviando] = useState(false)
  const [erro, definirErro] = useState('')

  async function aoEnviar(evento) {
    evento.preventDefault()
    definirErro('')
    definirEnviando(true)
    try {
      const token = await login(usuario, senha)
      aoLogar(token)
    } catch (erroLogin) {
      definirErro(erroLogin.message)
    } finally {
      definirEnviando(false)
    }
  }

  return (
    <div className="login-tela">
      <div className="login-cartao">
        <BarraMais />
        <div className="login-conteudo">
          <h1>Saldo+</h1>
          <p className="login-subtitulo">Assistente de suporte para professores</p>

          <form onSubmit={aoEnviar} className="login-formulario">
            <label htmlFor="campo-usuario">Usuário</label>
            <input
              id="campo-usuario"
              type="text"
              value={usuario}
              onChange={(evento) => definirUsuario(evento.target.value)}
              autoComplete="username"
              required
            />

            <label htmlFor="campo-senha">Senha</label>
            <input
              id="campo-senha"
              type="password"
              value={senha}
              onChange={(evento) => definirSenha(evento.target.value)}
              autoComplete="current-password"
              required
            />

            {erro && (
              <p className="login-erro" role="alert">
                {erro}
              </p>
            )}

            <button type="submit" disabled={enviando}>
              {enviando ? 'Entrando...' : 'Entrar'}
            </button>
          </form>

          <button type="button" className="login-link-secundario" onClick={aoEsqueciSenha}>
            Esqueci minha senha
          </button>
        </div>
      </div>
    </div>
  )
}

export default Login
