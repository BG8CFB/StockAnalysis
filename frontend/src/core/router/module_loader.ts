import { RouteRecordRaw } from 'vue-router'

export interface ModuleRoute {
  path: string
  name: string
  component: any
  meta?: {
    title?: string
    icon?: string
    requiresAuth?: boolean
    hideInMenu?: boolean
    order?: number
  }
  children?: ModuleRoute[]
}

export interface ModuleInfo {
  name: string
  version: string
  description?: string
  routes: ModuleRoute[]
}

class ModuleLoader {
  private loadedModules: Map<string, ModuleInfo> = new Map()
  private routes: RouteRecordRaw[] = []

  constructor() {
    this.loadModules()
  }

  private async loadModules() {
    try {
      // 使用Vite的glob动态导入所有模块路由文件
      const moduleFiles = import.meta.glob('../modules/*/routes.ts')

      for (const path in moduleFiles) {
        try {
          const module = await moduleFiles[path]() as any
          const moduleInfo = module.default as ModuleInfo

          if (moduleInfo && moduleInfo.name) {
            this.loadedModules.set(moduleInfo.name, moduleInfo)

            // 转换模块路由为Vue Router格式
            const vueRoutes = this.convertToVueRoutes(moduleInfo.routes, moduleInfo.name)
            this.routes.push(...vueRoutes)

            console.log(`Loaded module: ${moduleInfo.name} with ${vueRoutes.length} routes`)
          }
        } catch (error) {
          console.error(`Failed to load module from ${path}:`, error)
        }
      }
    } catch (error) {
      console.error('Failed to load modules:', error)
    }
  }

  private convertToVueRoutes(moduleRoutes: ModuleRoute[], moduleName: string): RouteRecordRaw[] {
    const vueRoutes: RouteRecordRaw[] = []

    for (const route of moduleRoutes) {
      const vueRoute: RouteRecordRaw = {
        path: route.path,
        name: route.name,
        component: route.component,
        meta: {
          ...route.meta,
          module: moduleName
        }
      }

      // 处理子路由
      if (route.children && route.children.length > 0) {
        vueRoute.children = this.convertToVueRoutes(route.children, moduleName)
      }

      vueRoutes.push(vueRoute)
    }

    return vueRoutes
  }

  // 获取所有路由
  getRoutes(): RouteRecordRaw[] {
    return this.routes
  }

  // 获取所有模块信息
  getLoadedModules(): ModuleInfo[] {
    return Array.from(this.loadedModules.values())
  }

  // 获取特定模块信息
  getModuleInfo(moduleName: string): ModuleInfo | undefined {
    return this.loadedModules.get(moduleName)
  }

  // 检查模块是否已加载
  isModuleLoaded(moduleName: string): boolean {
    return this.loadedModules.has(moduleName)
  }

  // 获取用于菜单的路由（排除隐藏的路由）
  getMenuRoutes(): RouteRecordRaw[] {
    return this.routes.filter(route => !route.meta?.hideInMenu)
  }

  // 根据路径获取模块信息
  getModuleByPath(path: string): ModuleInfo | undefined {
    for (const moduleInfo of this.loadedModules.values()) {
      for (const route of moduleInfo.routes) {
        if (this.pathMatchesRoute(path, route)) {
          return moduleInfo
        }
      }
    }
    return undefined
  }

  private pathMatchesRoute(path: string, route: ModuleRoute): boolean {
    if (route.path === path) {
      return true
    }

    if (route.children) {
      for (const child of route.children) {
        const fullPath = route.path + child.path
        if (path.startsWith(fullPath)) {
          return true
        }
      }
    }

    return false
  }

  // 动态添加模块
  async addModule(moduleInfo: ModuleInfo): Promise<void> {
    if (this.loadedModules.has(moduleInfo.name)) {
      console.warn(`Module ${moduleInfo.name} is already loaded`)
      return
    }

    this.loadedModules.set(moduleInfo.name, moduleInfo)

    const vueRoutes = this.convertToVueRoutes(moduleInfo.routes, moduleInfo.name)
    this.routes.push(...vueRoutes)

    console.log(`Added module: ${moduleInfo.name}`)
  }

  // 移除模块
  removeModule(moduleName: string): void {
    if (!this.loadedModules.has(moduleName)) {
      console.warn(`Module ${moduleName} is not loaded`)
      return
    }

    this.loadedModules.delete(moduleName)
    this.routes = this.routes.filter(route => route.meta?.module !== moduleName)

    console.log(`Removed module: ${moduleName}`)
  }
}

// 创建全局模块加载器实例
export const moduleLoader = new ModuleLoader()