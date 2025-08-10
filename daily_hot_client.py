from typing import List, Dict, Any, Optional

import requests
from loguru import logger

import config


class DailyHotClient:
    """
    热点数据客户端，用于获取各类平台的热点榜单数据
    """

    def __init__(self, base_url: str = "https://dailyhot.yueyong.fun"):
        """
        初始化客户端
        
        :param base_url: 热点服务的基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def get_all_categories(self) -> List[Dict[str, str]]:
        """
        获取所有可用的热点类目
        
        :return: 包含类目名称和路径的列表
        """
        try:
            response = self.session.get(f"{self.base_url}/all")
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200:
                return data.get("routes", [])
            else:
                logger.error(f"获取类目列表失败，错误码: {data.get('code')}")
                return []
        except Exception as e:
            logger.error(f"获取类目列表时发生错误: {e}")
            return []

    def get_hot_list(self, path: str) -> Optional[Dict[str, Any]]:
        """
        根据路径获取当前类目下的热点列表
        
        :param path: 类目的路径（例如: "/36kr"）
        :return: 热点列表数据
        """
        try:
            # 确保路径格式正确
            if not path.startswith('/'):
                path = '/' + path

            response = self.session.get(f"{self.base_url}{path}")
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200:
                return data
            else:
                logger.error(f"获取热点列表失败，路径: {path}, 错误码: {data.get('code')}")
                return None
        except Exception as e:
            logger.error(f"获取热点列表时发生错误，路径: {path}, 错误: {e}")
            return None

    def get_all_hot_lists(self) -> Dict[str, Any]:
        """
        获取所有类目的热点列表
        
        :return: 所有类目的热点数据
        """
        categories = self.get_all_categories()
        all_hot_data = {}

        for category in categories:
            path = category.get('path')
            name = category.get('name')

            logger.info(f"正在获取 {name} 的热点数据...")
            hot_data = self.get_hot_list(path)

            if hot_data:
                all_hot_data[name] = hot_data
            else:
                logger.warning(f"未能获取到 {name} 的热点数据")

        return all_hot_data

    def analyze_hot_item(self, url: str) -> Optional[Dict[str, Any]]:
        """
        调用外部API分析热点项的内容
        
        :param url: 热点项的URL
        :return: 包含摘要和标签的分析结果
        """
        if not url:
            logger.warning("无法分析空URL")
            return None

        try:
            # 调用外部API进行分析
            api_url = config.SUMMARIZER_API_URL
            payload = {"url": url}
            headers = {"Content-Type": "application/json"}

            response = requests.post(api_url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()

            # 解析API响应
            result = response.json()
            return {
                "summary": result.get("summary", ""),
                "tags": result.get("tags", [])
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API调用失败，URL: {url}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"分析热点项时发生错误，URL: {url}, 错误: {e}")
            return None


def main():
    """
    主函数，用于测试客户端功能
    """
    client = DailyHotClient()

    # 获取所有类目
    categories = client.get_all_categories()
    print("所有类目:")
    for category in categories:
        print(f"  - {category['name']}: {category['path']}")

    # 获取第一个类目的热点列表作为示例
    if categories:
        first_category = categories[0]
        print(f"\n正在获取 {first_category['name']} 的热点列表...")
        hot_list = client.get_hot_list(first_category['path'])
        if hot_list:
            print(f"标题: {hot_list.get('title', 'N/A')}")
            print(f"类型: {hot_list.get('type', 'N/A')}")
            print(f"更新时间: {hot_list.get('updateTime', 'N/A')}")
            print(f"数据条数: {len(hot_list.get('data', []))}")

            # 显示前几条热点数据
            hot_data = hot_list.get('data', [])
            for i, item in enumerate(hot_data[:3]):
                print(f"  {i + 1}. {item.get('title', 'N/A')}")

            # 测试分析功能
            if hot_data and hot_data[0].get('url'):
                print(f"\n正在分析第一条热点数据...")
                analysis_result = client.analyze_hot_item(hot_data[0].get('url'))
                if analysis_result:
                    print(f"摘要: {analysis_result['summary'][:100]}...")
                    print(f"标签: {', '.join(analysis_result['tags'][:5])}")
                else:
                    print("分析失败")
        else:
            print(f"未能获取到 {first_category['name']} 的热点列表")


if __name__ == "__main__":
    main()
