import { prisma } from "@/lib/prisma";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Metadata } from "next";

export const revalidate = 3600;

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
    const post = await prisma.blogPost.findUnique({
        where: { slug: params.slug },
    });

    if (!post) {
        return { title: "Post no encontrado" };
    }

    return {
        title: `${post.title} | Blog ReportPilot`,
        description: post.excerpt,
        keywords: post.seoKeywords,
    };
}

export default async function BlogPostPage({ params }: { params: { slug: string } }) {
    const post = await prisma.blogPost.findUnique({
        where: { slug: params.slug },
    });

    if (!post) {
        notFound();
    }

    return (
        <div className="min-h-screen bg-[#0a0e1a] text-white">
            <div className="max-w-3xl mx-auto px-6 py-20">
                <Link href="/blog" className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-2 mb-12">
                    &larr; Volver al blog
                </Link>

                <article>
                    <header className="mb-12">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm font-bold shadow-lg">
                                AR
                            </div>
                            <div>
                                <p className="font-medium text-gray-200">{post.publishedBy}</p>
                                <p className="text-sm text-gray-500">
                                    {post.createdAt.toLocaleDateString("es-ES", { year: "numeric", month: "long", day: "numeric" })}
                                </p>
                            </div>
                        </div>
                        <h1 className="text-3xl md:text-5xl font-bold mb-6 text-white tracking-tight leading-tight">
                            {post.title}
                        </h1>
                        <p className="text-xl text-blue-200/80 leading-relaxed font-light">
                            {post.excerpt}
                        </p>
                    </header>

                    {/* Contenido HTML generado por AI */}
                    <div
                        className="prose prose-invert prose-blue max-w-none 
                                   prose-p:text-gray-300 prose-p:leading-relaxed prose-p:mb-6
                                   prose-h2:text-white prose-h2:font-bold prose-h2:mt-12 prose-h2:mb-6 prose-h2:text-2xl
                                   prose-h3:text-gray-200 prose-h3:font-bold prose-h3:mt-8 prose-h3:mb-4 prose-h3:text-xl
                                   prose-strong:text-blue-400 
                                   prose-blockquote:border-blue-500 prose-blockquote:bg-blue-500/5 prose-blockquote:px-6 prose-blockquote:py-2 prose-blockquote:rounded-r-lg prose-blockquote:italic
                                   prose-ul:text-gray-300 prose-ul:my-6
                                   prose-li:my-2"
                        dangerouslySetInnerHTML={{ __html: post.contentHtml }}
                    />
                </article>

                <div className="mt-20 p-8 bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-2xl text-center">
                    <h3 className="text-2xl font-bold mb-4">¿Te sirven estos datos?</h3>
                    <p className="text-gray-400 mb-6 max-w-lg mx-auto">
                        ReportPilot automatiza reportes para agencias de marketing, conectando GA4 y Meta Ads con inteligencia artificial.
                    </p>
                    <a href="https://reportpilot.com/login" className="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-colors">
                        Prueba gratis 14 días
                    </a>
                </div>
            </div>
        </div>
    );
}
