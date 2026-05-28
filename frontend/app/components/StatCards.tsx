type Props = {
  title: string;
  value: string;
  color?: string;
};

export default function StatCards({
  title,
  value,
  color,
}: Props) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <h3 className="text-slate-500 text-sm">
        {title}
      </h3>

      <h1
        className={`text-4xl font-bold mt-3 ${
          color || "text-slate-800"
        }`}
      >
        {value}
      </h1>
    </div>
  );
}