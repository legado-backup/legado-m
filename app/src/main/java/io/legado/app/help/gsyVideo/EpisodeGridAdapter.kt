package io.legado.app.help.gsyVideo

import android.content.Context
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import io.legado.app.R

/**
 * 选集网格适配器（video-cache-and-multiep R7 / V4）。
 *
 * 取代历史 ListView 单列适配器（`SwitchVideoAdapter` 已随分组弹框退役删除）：
 * 样式统一由 [applyVideoChoiceItemStyle] 提供。
 *
 * @param currentSelection 组内当前集下标（-1 表示当前集不在本组）
 * @param onItemClick 回调参数为**组内下标**（调用方负责叠加分组起点得到全集下标）
 */
class EpisodeGridAdapter(
    private val context: Context,
    private val titles: List<String>,
    private val currentSelection: Int,
    private val onItemClick: (Int) -> Unit,
) : RecyclerView.Adapter<EpisodeGridAdapter.Holder>() {

    class Holder(val textView: TextView) : RecyclerView.ViewHolder(textView)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): Holder {
        val view = LayoutInflater.from(context)
            .inflate(R.layout.item_video_episode_chip, parent, false)
        return Holder(view as TextView)
    }

    override fun onBindViewHolder(holder: Holder, position: Int) {
        holder.textView.text = titles.getOrNull(position).orEmpty()
        applyVideoChoiceItemStyle(context, holder.textView, position == currentSelection)
        holder.textView.setOnClickListener { onItemClick(position) }
    }

    override fun getItemCount(): Int = titles.size
}
