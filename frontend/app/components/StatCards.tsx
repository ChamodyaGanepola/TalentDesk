type Props = {
  title: string;
  value: string | number;
  color?: string;
};

export default function StatCard({ title, value, color }: Props) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 className="text-slate-500 text-sm">{title}</h3>

      <h1 className={`text-4xl font-bold mt-3 ${color || "text-slate-800"}`}>
        {value}
      </h1>
    </div>
  );
}