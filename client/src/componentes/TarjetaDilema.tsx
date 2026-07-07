interface Props {
  opcion1: string
  opcion2: string
}

export default function TarjetaDilema({ opcion1, opcion2 }: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div className="rounded-2xl border-2 border-opcion-1/40 bg-opcion-1/10 p-5 text-center">
        <p className="mb-1 text-xs font-semibold tracking-wide text-opcion-1 uppercase">
          Opción 1
        </p>
        <p className="font-display text-lg text-white">{opcion1}</p>
      </div>
      <div className="rounded-2xl border-2 border-opcion-2/40 bg-opcion-2/10 p-5 text-center">
        <p className="mb-1 text-xs font-semibold tracking-wide text-opcion-2 uppercase">
          Opción 2
        </p>
        <p className="font-display text-lg text-white">{opcion2}</p>
      </div>
    </div>
  )
}
