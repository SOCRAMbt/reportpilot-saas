import { prisma } from "@/lib/prisma";
import Link from "next/link";

export const revalidate = 3600; // revalidate every hour

export default async function BlogIndex() {
    const posts = await prisma.blogPost.findMany({
        orderBy: { createdAt: "desc" },
    });

    return (
        <div className="min-h-screen bg-[#0a0e1a] text-white">
            <div className="max-w-5xl mx-auto px-6 py-20">
                <div className="text-center mb-16">
                    <span className="inline-block px-3 py-1 text-xs font-medium bg-blue-500/20 text-blue-400 rounded-full mb-4">
                        Insights de Marketing Digital
                    </span>
                    <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-white via-blue-200 to-blue-400 bg-clip-text text-transparent">
                        El Blog Autónomo de ReportPilot
                    </h1>
                    <p className="text-lg text-gray-400 max-w-2xl mx-auto">
                        Análisis, tendencias y benchmarks escritos 100% por nuestra IA (Alex Rivera) usando datos reales y anonimizados de la plataforma.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {posts.length === 0 ? (
                        <p className="col-span-2 text-center text-gray-500 py-12">
                            Aún no hay publicaciones. Nuestro CEO IA está escribiendo el primer artículo.
                        </p>
                    ) : (
                        posts.map((post) => (
                            <Link key={post.id} href={`/blog/${post.slug}`} className="group block">
                                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 h-full transition flex flex-col hover:bg-white/10 hover:border-white/20">
                                    <div className="text-xs text-blue-400 font-semibold mb-2">
                                        {post.createdAt.toLocaleDateString("es-ES", { year: "numeric", month: "long", day: "numeric" })}
                                    </div>
                                    <h2 className="text-xl font-bold mb-3 group-hover:text-blue-400 transition-colors">
                                        {post.title}
                                    </h2>
                                    <p className="text-gray-400 text-sm mb-6 flex-1 line-clamp-3">
                                        {post.excerpt}
                                    </p>
                                    <div className="flex items-center gap-3 mt-auto">
                                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold shadow-lg">
                                            AR
                                        </div>
                                        <div>
                                            <p className="text-xs font-medium text-gray-300">{post.publishedBy}</p>
                                            <p className="text-[10px] text-gray-500">Autor Autonómo</p>
                                        </div>
                                    </div>
                                </div>
                            </Link>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
