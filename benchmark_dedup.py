#!/usr/bin/env python3
"""
性能基准测试：对比优化前后的去重性能

运行方式：python benchmark_dedup.py
"""

import time
import sys
from pathlib import Path

# Make the src package importable
sys.path.insert(0, str(Path(__file__).parent / "src"))

from collector import _deduplicate_articles


def generate_test_articles(num_sources: int, articles_per_source: int) -> dict:
    """生成测试数据"""
    articles_by_source = {}

    for i in range(num_sources):
        articles = []
        for j in range(articles_per_source):
            # Create articles with varying similarity
            base_text = f"Article {j} from source {i}"
            if j % 3 == 0:
                # Some duplicates
                title = "Breaking news about technology"
                summary = "A major tech company announced a new product today"
            elif j % 3 == 1:
                # Some similar
                title = f"Technology news update {j}"
                summary = f"Important development in the tech industry regarding innovation and growth {j}"
            else:
                # Mostly unique
                title = f"Unique article {i}_{j} with specific content"
                summary = f"This is a completely unique story about event {i}_{j} that happened recently"

            articles.append({
                "title": title,
                "link": f"http://source{i}.com/article{j}",
                "summary": summary,
                "published": ""
            })

        articles_by_source[f"Source{i}"] = {
            "articles": articles,
            "categories": ["tech"]
        }

    return articles_by_source


def benchmark_deduplication():
    """性能基准测试"""
    print("=" * 70)
    print("新闻去重性能基准测试")
    print("=" * 70)

    test_cases = [
        (5, 10, "小规模"),    # 50 articles
        (10, 20, "中规模"),   # 200 articles
        (20, 25, "大规模"),   # 500 articles
    ]

    for num_sources, articles_per_source, scale in test_cases:
        total_articles = num_sources * articles_per_source
        print(f"\n【{scale}测试】")
        print(f"  新闻源数量: {num_sources}")
        print(f"  每源文章数: {articles_per_source}")
        print(f"  总文章数: {total_articles}")

        # Generate test data
        articles = generate_test_articles(num_sources, articles_per_source)

        # Benchmark
        start_time = time.time()
        result = _deduplicate_articles(articles, similarity_threshold=0.7)
        end_time = time.time()

        elapsed = (end_time - start_time) * 1000  # Convert to milliseconds

        original_count = sum(len(data['articles']) for data in articles.values())
        final_count = sum(len(data['articles']) for data in result.values())
        removed_count = original_count - final_count

        print(f"  执行时间: {elapsed:.2f} ms")
        print(f"  去重前: {original_count} 篇")
        print(f"  去重后: {final_count} 篇")
        print(f"  移除: {removed_count} 篇 ({removed_count/original_count*100:.1f}%)")
        print(f"  平均每篇耗时: {elapsed/original_count:.3f} ms")

    print("\n" + "=" * 70)
    print("性能优化说明:")
    print("=" * 70)
    print("1. 预计算优化: 每篇文章的shingles只计算一次")
    print("2. 快速过滤: 文本长度差异>50%时直接跳过相似度计算")
    print("3. 使用3-shingles: 比单词集合更准确地捕捉上下文")
    print("4. 集合运算: 使用Python内置集合操作，C语言级别优化")
    print("\n理论时间复杂度: O(n²) 最坏情况")
    print("实际时间复杂度: O(n·m) 其中 m << n (通过快速过滤)")
    print("=" * 70)


if __name__ == "__main__":
    benchmark_deduplication()
