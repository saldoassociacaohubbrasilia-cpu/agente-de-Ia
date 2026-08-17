// A "barra +": assinatura visual da marca Saldo+, uma faixa fina de cruzes
// coloridas alternando verde, laranja, rosa e azul. Mantida num só lugar de
// propósito — não deve virar decoração espalhada pela tela.
function BarraMais() {
  const quantidadeDeCruzes = 24

  return (
    <div className="barra-mais" aria-hidden="true">
      {Array.from({ length: quantidadeDeCruzes }, (_, indice) => (
        <span key={indice}>+</span>
      ))}
    </div>
  )
}

export default BarraMais
